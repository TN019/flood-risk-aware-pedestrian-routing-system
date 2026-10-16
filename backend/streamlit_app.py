"""Interim Streamlit map UI for the routing engine, until the web frontend replaces it.

Risk-aware walking routes under flood scenarios built from official flood extents and terrain,
for a traveller's own wading limit.

Run (from backend/):  uv run streamlit run streamlit_app.py
"""

from __future__ import annotations

import time

import folium
import geopandas as gpd
import streamlit as st
from pyproj import Transformer
from shapely.geometry import Point
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

from floodroute import config
from floodroute import places as pl
from floodroute.hazard.catalog import NONE, list_scenarios, load_hazard
from floodroute.network import is_snappable, load_graph, to_gdfs
from floodroute.places.refuges import RefugeIndex
from floodroute.risk import DRY_DEPTH_M, HARD_LIMIT_M, BodyPart, TravellerProfile
from floodroute.risk.alerts import AlertLevel
from floodroute.risk.preference import DEFAULT_PREFERENCE, RoutePreference, explain
from floodroute.routing import RECOMMENDED, SAFE_SHORTEST, SHORTEST, RoutePlan, Router, RoutingError
from floodroute.sources import geocoding as geocode
from floodroute.trip import ONLY_OPTION, TripPlan, plan_trip

GRAPH_PATH = config.PROCESSED_NETWORK_PATH
PLACES_PATH = config.PROCESSED_PLACES_PATH
START, DEST = "Start", "Destination"
CHOOSE, CURRENT = "A point I choose", "My current location"

NETWORK_COLOUR = "#4a6f94"
ROUTE_COLOUR = "#7b2cbf"
WATER_COLOUR = "#1f78b4"
OVER_LIMIT_COLOUR = "#d62728"
# How each of the three planned routes is drawn and named.
OPTION_STYLE = {
    SHORTEST: ("#555555", 4, "8 6", "Shortest, ignoring flooding"),
    SAFE_SHORTEST: ("#e6550d", 5, "2 6", "Shortest within your limit"),
    RECOMMENDED: (ROUTE_COLOUR, 7, None, "Recommended"),
}
SOS_UNDO_SECONDS = 5
START_COLOUR = "green"
DEST_COLOUR = "red"

to_metric = Transformer.from_crs(config.WGS84, config.METRIC_CRS, always_xy=True)
to_wgs = Transformer.from_crs(config.METRIC_CRS, config.WGS84, always_xy=True)

st.set_page_config(page_title="Southbank Routing", page_icon="🗺️", layout="wide")


# --------------------------------------------------------------------------- data


@st.cache_resource
def load_router() -> Router:
    return Router(load_graph(GRAPH_PATH))


@st.cache_resource
def load_places() -> pl.PlaceResolver:
    return pl.PlaceResolver(
        gpd.read_file(PLACES_PATH, layer="buildings"),
        gpd.read_file(PLACES_PATH, layer="entrances"),
        load_router().footpaths,
    )


@st.cache_resource
def load_refuges() -> RefugeIndex:
    graph = load_router().graph
    return RefugeIndex(load_places(), graph.graph["study_area"].buffer(graph.graph["buffer_m"]))


@st.cache_resource
def load_hazards() -> dict:
    """Scenario title -> (definition, hazard provider), from normal conditions to the most severe."""
    return {info.title: (info, load_hazard(info)) for info in list_scenarios()}


@st.cache_resource
def official_extents() -> dict | None:
    """The official flood overlays near Southbank (LSIO / SBO), for context on the map."""
    if not config.FLOOD_OVERLAYS_PATH.exists():
        return None
    graph = load_router().graph
    near = graph.graph["study_area"].buffer(graph.graph["buffer_m"])
    overlays = gpd.read_file(config.FLOOD_OVERLAYS_PATH).to_crs(config.METRIC_CRS)
    overlays = overlays[overlays.intersects(near)][["zone_code", "zone_description", "geometry"]]
    return overlays.to_crs(config.WGS84).__geo_interface__


@st.cache_resource
def flood_features(title: str) -> dict:
    """Official extents and wet edges of a scenario, as WGS84 GeoJSON with depths."""
    info, hazard = load_hazards()[title]
    if info.method == NONE:
        return {"zones": None, "edges": []}
    graph = load_router().graph
    snapshot = hazard.snapshot(graph)
    by_id = {d["edge_id"]: d for *_, d in graph.edges(data=True)}
    edges = [
        {"depth_m": c.depth_m, "geometry": by_id[eid]["geometry"]}
        for eid, c in snapshot.conditions.items()
        if c.depth_m is not None
    ]
    edges = gpd.GeoDataFrame(edges, crs=config.METRIC_CRS).to_crs(config.WGS84) if edges else None
    return {
        "zones": official_extents(),
        "edges": [] if edges is None else [(r.depth_m, r.geometry.__geo_interface__) for r in edges.itertuples()],
    }


@st.cache_resource
def base_layers() -> dict:
    """GeoJSON for the static layers, computed once. The folium Map itself must be rebuilt each run."""
    graph = load_router().graph
    _, edges = to_gdfs(graph)
    edges["avoided"] = edges["cost_factor"].fillna(1) > 1 if "cost_factor" in edges else False
    streets = edges[[is_snappable(d) for *_, d in graph.edges(data=True)]]
    streets = streets[["in_study_area", "avoided", "geometry"]].to_crs(config.WGS84)
    paths, roads = streets[~streets.avoided], streets[streets.avoided]
    area = gpd.GeoSeries([graph.graph["study_area"]], crs=graph.graph["crs"])
    west, south, east, north = area.to_crs(config.WGS84).total_bounds
    return {
        "centre": [(south + north) / 2, (west + east) / 2],
        "ring": area.buffer(graph.graph["buffer_m"]).to_crs(config.WGS84).__geo_interface__,
        "area": area.to_crs(config.WGS84).__geo_interface__,
        "buffer_streets": paths[~paths.in_study_area][["geometry"]].__geo_interface__,
        "area_streets": paths[paths.in_study_area][["geometry"]].__geo_interface__,
        "avoided_roads": roads[["geometry"]].__geo_interface__,
    }


def base_map() -> folium.Map:
    layers = base_layers()
    fmap = folium.Map(location=layers["centre"], zoom_start=15, tiles="OpenStreetMap", max_zoom=20)
    folium.GeoJson(
        layers["ring"],
        style_function=lambda _: {"color": "#777", "weight": 1.5, "dashArray": "6 6", "fill": False},
        interactive=False,
    ).add_to(fmap)
    folium.GeoJson(
        layers["avoided_roads"],
        style_function=lambda _: {"color": "#999", "weight": 1.5, "opacity": 0.5, "dashArray": "4 6"},
        interactive=False,
    ).add_to(fmap)
    folium.GeoJson(
        layers["buffer_streets"],
        style_function=lambda _: {"color": NETWORK_COLOUR, "weight": 2, "opacity": 0.3},
        interactive=False,
    ).add_to(fmap)
    folium.GeoJson(
        layers["area_streets"],
        style_function=lambda _: {"color": NETWORK_COLOUR, "weight": 2.5, "opacity": 0.8},
        interactive=False,
    ).add_to(fmap)
    folium.GeoJson(
        layers["area"], style_function=lambda _: {"color": "#111", "weight": 3, "fill": False}, interactive=False
    ).add_to(fmap)
    return fmap


@st.cache_data(show_spinner=False)
def search_places(query: str) -> list[geocode.SearchResult]:
    graph = load_router().graph
    ring = gpd.GeoSeries([graph.graph["study_area"]], crs=graph.graph["crs"]).buffer(graph.graph["buffer_m"])
    return geocode.search(query, tuple(ring.to_crs(config.WGS84).total_bounds))


def to_point(latlon: tuple[float, float]) -> Point:
    return Point(*to_metric.transform(latlon[1], latlon[0]))


def to_latlon(p: Point) -> tuple[float, float]:
    lon, lat = to_wgs.transform(p.x, p.y)
    return lat, lon


def in_southbank(latlon: tuple[float, float]) -> bool:
    return load_router().study_area.covers(to_point(latlon))


def to_metric_geom(geom):
    return None if geom is None else gpd.GeoSeries([geom], crs=config.WGS84).to_crs(config.METRIC_CRS).iloc[0]


def resolve(which: str) -> pl.Place:
    """Where routing may start/end for the chosen point: a building's entrances, or the point itself."""
    latlon, footprint, label = (
        (state.start, state.start_fp, state.start_label)
        if which == START
        else (state.dest, state.dest_fp, state.dest_label)
    )
    role = pl.ORIGIN if which == START else pl.DESTINATION
    return load_places().resolve(to_point(latlon), label or "chosen point", to_metric_geom(footprint), role)


# --------------------------------------------------------------------------- state

state = st.session_state
for key, default in {
    "start": None,
    "dest": None,
    "start_src": None,
    "dest_src": None,
    "start_fp": None,
    "dest_fp": None,
    "start_label": None,
    "dest_label": None,
    "click_target": START,
    "last_click": None,
}.items():
    state.setdefault(key, default)


def set_point(which: str, latlon: tuple[float, float], source: str, footprint=None, label=None) -> None:
    if which == START:
        state.start, state.start_src, state.start_fp, state.start_label = latlon, source, footprint, label
        if state.dest is None:
            # The radio widget owning click_target may already be drawn this run; switch on the next run.
            state.next_click_target = DEST
    else:
        state.dest, state.dest_src, state.dest_fp, state.dest_label = latlon, source, footprint, label


def search_box(which: str) -> None:
    query = st.text_input(f"Search {which.lower()}", key=f"q_{which}", placeholder="e.g. Eureka Tower, 1 City Road")
    if not query:
        return
    try:
        places = search_places(query)
    except Exception as exc:  # network / service errors
        st.error(f"Search failed: {exc}")
        return
    if not places:
        st.caption("No match inside Southbank.")
        return
    labels = [p.label for p in places]
    choice = st.selectbox(
        "Matches",
        range(len(places)),
        format_func=lambda i: labels[i][:80],
        key=f"pick_{which}",
        label_visibility="collapsed",
    )
    if st.button(f"Use as {which.lower()}", key=f"use_{which}", width="stretch"):
        hit = places[choice]
        set_point(which, (hit.lat, hit.lon), "search", hit.footprint, hit.label.split(",")[0])
        st.rerun()


# --------------------------------------------------------------------------- sidebar

with st.sidebar:
    st.header("Southbank Routing")
    st.caption(
        "Shortest walking route on the OpenStreetMap walking network (indoor corridors excluded; "
        "routes prefer sidewalks over walking along roads). Flood conditions are not applied yet."
    )

    mode = st.radio("Start from", [CHOOSE, CURRENT], horizontal=True)
    gps_ok = False
    if mode == CURRENT:
        loc = get_geolocation(component_key="geo")
        if loc is None:
            st.info("Waiting for your browser to share its location…")
        elif "coords" in loc:
            gps = (loc["coords"]["latitude"], loc["coords"]["longitude"])
            if in_southbank(gps):
                gps_ok = True
                if state.start != gps:
                    set_point(START, gps, "current location")
            else:
                km = load_router().study_area.distance(to_point(gps)) / 1000
                st.warning(
                    f"Your location is {km:.1f} km outside Southbank. "
                    "Click the map to set a simulated current location instead."
                )
        else:
            st.warning(
                "Location unavailable (permission denied or not supported). "
                "Click the map to set a simulated current location instead."
            )
    if mode == CHOOSE:
        search_box(START)
    search_box(DEST)

    st.divider()
    scenario_title = st.selectbox("Flood scenario", list(load_hazards()))
    scenario_info, hazard = load_hazards()[scenario_title]
    st.caption(scenario_info.description)
    if scenario_info.params.get("sources"):
        with st.expander("Sources"):
            st.markdown("\n".join(f"- {source}" for source in scenario_info.params["sources"]))
    height_cm = st.number_input("Your height (cm)", min_value=60, max_value=230, value=170, step=1)
    if "next_wading_part" in state:  # set by "use this limit"; widgets may only change before they render
        state.wading_part = state.pop("next_wading_part")
    state.setdefault("wading_part", BodyPart.ANKLE)
    part = st.selectbox(
        "Deepest water you will walk through", list(BodyPart), key="wading_part", format_func=lambda b: b.label
    )
    wheelchair = st.checkbox("I use a wheelchair or mobility aid")
    profile = TravellerProfile(height_cm / 100, part, uses_wheelchair=wheelchair)
    st.caption(f"Your limit: **{profile.depth_limit_m * 100:.0f} cm** (never more than {HARD_LIMIT_M * 100:.0f} cm)")
    preference = st.radio(
        "Route preference",
        list(RoutePreference),
        index=list(RoutePreference).index(DEFAULT_PREFERENCE),
        format_func=lambda p: p.label,
        captions=[p.summary for p in RoutePreference],
        help="Water deeper than your limit is always avoided. This only decides whether water within "
        "your limit is worth walking around.",
    )
    alpha = preference.alpha
    with st.expander("Advanced"):
        if st.checkbox("Set the risk weight α directly"):
            alpha = st.slider(
                "Risk weight α",
                0.0,
                20.0,
                preference.alpha,
                0.5,
                help="Extra metres worth walking to avoid one metre of water right at your limit.",
            )
        else:
            st.caption(f"{preference.label} uses α = {preference.alpha:g}.")
    st.caption(explain(alpha, profile))

    st.divider()
    options = [DEST] if gps_ok else [START, DEST]
    if "next_click_target" in state:
        state.click_target = state.pop("next_click_target")
    if state.click_target not in options:
        state.click_target = DEST
    st.radio("A map click sets the", options, key="click_target", horizontal=True)

    for label, latlon, src in ((START, state.start, state.start_src), (DEST, state.dest, state.dest_src)):
        st.markdown(f"**{label}:** " + (f"{latlon[0]:.5f}, {latlon[1]:.5f} · {src}" if latlon else "not set"))
    if st.button("Clear points", width="stretch"):
        for key in ("start", "dest", "start_src", "dest_src", "start_fp", "dest_fp", "start_label", "dest_label"):
            state[key] = None
        state.click_target = START
        st.rerun()


# --------------------------------------------------------------------------- route + map

router = load_router()
snapshot = hazard.snapshot(router.graph)
trip: TripPlan | None = None
error, ends = None, {}
if state.start and state.dest:
    if not (in_southbank(state.start) and in_southbank(state.dest)):
        error = "Start and destination must both be inside Southbank (the black boundary)."
    else:
        ends = {START: resolve(START), DEST: resolve(DEST)}
        try:
            trip = plan_trip(router, load_refuges(), ends[START], ends[DEST], snapshot, profile, alpha)
        except RoutingError as exc:
            error = str(exc)
plan: RoutePlan | None = trip.routes if trip else None
route = plan.recommended.route if plan else None
REFUGE_COLOUR = "#2ca02c"
DOWNGRADE_COLOUR = "#b07cd8"

overlay = folium.FeatureGroup(name="route")
flood = flood_features(scenario_title)
if flood["zones"]:
    folium.GeoJson(
        flood["zones"],
        style_function=lambda f: {
            "color": WATER_COLOUR,
            "weight": 1,
            "dashArray": "4 4",
            "fillColor": WATER_COLOUR,
            "fillOpacity": 0.08,
        },
        tooltip=folium.GeoJsonTooltip(["zone_code", "zone_description"], aliases=["Overlay", "Official extent"]),
    ).add_to(overlay)
for depth, geom in flood["edges"]:  # wet footpaths: red where deeper than this traveller's limit
    over = depth > profile.depth_limit_m
    folium.GeoJson(
        geom,
        style_function=lambda _, o=over: {
            "color": OVER_LIMIT_COLOUR if o else WATER_COLOUR,
            "weight": 5,
            "opacity": 0.9,
            "dashArray": "6 4" if o else None,
        },
        tooltip=f"{depth * 100:.0f} cm · {profile.describe_depth(depth)}" + (" · over your limit" if over else ""),
    ).add_to(overlay)
for which, place in ends.items():  # the building a start/destination resolved to, and its usable doors
    colour = START_COLOUR if which == START else DEST_COLOUR
    if place.building is not None:
        folium.GeoJson(
            gpd.GeoSeries([place.building], crs=config.METRIC_CRS).to_crs(config.WGS84).__geo_interface__,
            style_function=lambda _, c=colour: {"color": c, "weight": 2, "fillOpacity": 0.12},
            tooltip=place.label,
        ).add_to(overlay)
        for a in place.access:
            folium.CircleMarker(
                to_latlon(a.point),
                radius=4,
                color=colour,
                fill=True,
                fill_opacity=0.6,
                tooltip=f"{place.label}: {a.label}",
            ).add_to(overlay)
if plan is not None:
    # Draw each distinct route once; where options coincide, use the style of the most important one.
    groups: list[tuple[object, list[str]]] = []
    for option in plan.options:
        if not option.found:
            continue
        match = next((g for g in groups if g[0].geometry.equals(option.route.geometry)), None)
        if match:
            match[1].append(option.kind)
        else:
            groups.append((option.route, [option.kind]))
    for drawn_route, kinds in sorted(groups, key=lambda g: RECOMMENDED in g[1]):  # recommended on top
        colour, weight, dash, _ = OPTION_STYLE[RECOMMENDED if RECOMMENDED in kinds else kinds[0]]
        folium.PolyLine(
            [to_latlon(Point(c)) for c in drawn_route.geometry.coords],
            color=colour,
            weight=weight,
            opacity=0.9,
            dash_array=dash,
            tooltip=" = ".join(OPTION_STYLE[k][3] for k in kinds) + f": {drawn_route.length_m:,.0f} m",
        ).add_to(overlay)
if trip is not None and trip.downgrade is not None:
    folium.PolyLine(
        [to_latlon(Point(c)) for c in trip.downgrade.option.route.geometry.coords],
        color=DOWNGRADE_COLOUR,
        weight=5,
        opacity=0.9,
        dash_array="10 6",
        tooltip=f"With a {trip.downgrade.body_part.label} limit: {trip.downgrade.option.route.length_m:,.0f} m",
    ).add_to(overlay)
if trip is not None and trip.refuge is not None:
    folium.PolyLine(
        [to_latlon(Point(c)) for c in trip.refuge.route.geometry.coords],
        color=REFUGE_COLOUR,
        weight=6,
        opacity=0.9,
        tooltip=f"To shelter: {trip.refuge.refuge.name}, {trip.refuge.route.length_m:,.0f} m",
    ).add_to(overlay)
    folium.GeoJson(
        gpd.GeoSeries([trip.refuge.refuge.building], crs=config.METRIC_CRS).to_crs(config.WGS84).__geo_interface__,
        style_function=lambda _: {"color": REFUGE_COLOUR, "weight": 2, "fillOpacity": 0.25},
        tooltip=f"Shelter: {trip.refuge.refuge.name}",
    ).add_to(overlay)
if route is not None:
    for snap in (route.origin, route.destination):  # short walk between the door/point and the footpath
        folium.PolyLine(
            [to_latlon(snap.point), to_latlon(snap.snapped)], color=ROUTE_COLOUR, weight=3, dash_array="4 6"
        ).add_to(overlay)
for which, colour in ((START, START_COLOUR), (DEST, DEST_COLOUR)):
    latlon = state.start if which == START else state.dest
    if route is not None:  # mark the door actually used rather than the middle of the building
        latlon = to_latlon((route.origin if which == START else route.destination).point)
    if latlon:
        folium.Marker(
            latlon, tooltip=which, icon=folium.Icon(color=colour, icon="flag" if which == DEST else "user", prefix="fa")
        ).add_to(overlay)


def depth_text(depth: float | None) -> str:
    if depth is None:
        return "unknown"
    return "none" if depth <= DRY_DEPTH_M else f"{depth * 100:.0f} cm ({profile.describe_depth(depth)})"


def show_origin_and_emergency(trip: TripPlan) -> None:
    """The alert for where the traveller stands, and the emergency panel."""
    o = trip.origin
    depth = "unknown" if o.depth_m is None else f"{o.depth_m * 100:.0f} cm"
    if o.sheltered and not trip.has_safe_route:
        st.info(
            f"You are starting inside {ends[START].label}. No route keeps you within your limit, so the safest "
            "choice is to stay inside until the water goes down."
        )
    if o.level == AlertLevel.OVER_LIMIT:
        st.warning(f"You are standing in {depth} of water ({o.depth_label}), deeper than your limit.")
    elif o.level == AlertLevel.DEEP:
        st.warning(f"⚠️ You are standing in {depth} of water ({o.depth_label}). Move carefully; help is available.")
    elif o.level == AlertLevel.VERY_DEEP:
        st.error(f"🟠 Water here is {depth}, above your knee. Calling for help is recommended before moving.")
    elif o.level == AlertLevel.CRITICAL:
        st.error(f"🔴 Water here is {depth} ({o.depth_label}). Stay where you are if you can and call for help now.")
    if trip.emergency is None:
        return
    advice = trip.emergency.advice
    title = "Emergency help — " + ("your only option" if advice == ONLY_OPTION else advice)
    with st.container(border=True):
        st.markdown(f"**{title}**")
        if advice == ONLY_OPTION:
            st.caption("No shelter can be reached from here. Stay on the highest ground you can reach.")
        c1, c2 = st.columns(2)
        c1.link_button("📞 Call 000", "tel:000", type="primary", width="stretch")
        if state.get("sos_sent_at") is None:
            if c2.button("📣 Alert people nearby (SOS)", width="stretch"):
                state.sos_sent_at = time.time()
                st.rerun()
        else:
            sent = time.time() - state.sos_sent_at
            c2.success(f"SOS sent {sent:.0f} s ago with your location and {depth} water depth (simulated).")
            if sent < SOS_UNDO_SECONDS and c2.button("Undo SOS", width="stretch"):
                state.sos_sent_at = None
                st.rerun()


def show_alternatives(trip: TripPlan) -> None:
    if trip.downgrade is not None:
        d = trip.downgrade
        m = d.option.metrics
        with st.container(border=True):
            st.markdown(
                f"**Accept water up to the {d.body_part.label} ({d.depth_limit_m * 100:.0f} cm)?** "
                f"Then you can get there: {m.length_m:,.0f} m, deepest {m.max_depth_m * 100:.0f} cm "
                f"({m.max_depth_label}). Dashed light purple on the map."
            )
            if st.button(f"Use the {d.body_part.label} limit"):
                state.next_wading_part = d.body_part
                st.rerun()
    if trip.refuge is not None:
        r = trip.refuge
        m = r.metrics
        text = (
            f"**Shelter nearby: {r.refuge.name}** ({r.entrance_label}), {m.length_m:,.0f} m, "
            f"deepest water {'none' if not m.max_depth_m or m.max_depth_m <= DRY_DEPTH_M else m.max_depth_label}. "
            "Green on the map. Wait there until the water goes down; this is based on current conditions only."
        )
        if not r.within_limit:
            text += " ⚠️ The way there crosses water deeper than your limit; it is the shallowest way out."
        if trip.origin.level == AlertLevel.CRITICAL:
            with st.expander("If you cannot wait for help: route to shelter"):
                st.markdown(text)
        else:
            with st.container(border=True):
                st.markdown(text)


if trip is not None:
    show_origin_and_emergency(trip)
    if not trip.has_safe_route:
        show_alternatives(trip)
if error:
    st.error(error)
elif plan is None and trip is not None:
    st.error("No route connects these points.")
elif plan is not None:
    if route is not None:
        m = plan.recommended.metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Walking distance",
            f"{m.length_m:,.0f} m",
            f"+{m.detour_ratio:.0%} vs shortest" if m.detour_ratio and m.detour_ratio > 0.005 else None,
            delta_color="off",
        )
        c2.metric("Estimated time", f"{m.travel_time_s / 60:.0f} min")
        c3.metric(
            "Deepest water",
            "none" if not m.max_depth_m or m.max_depth_m <= DRY_DEPTH_M else f"{m.max_depth_m * 100:.0f} cm",
            m.max_depth_label if m.max_depth_m and m.max_depth_m > DRY_DEPTH_M else None,
            delta_color="off",
        )
        c4.metric("Distance in water", f"{m.wading_length_m:,.0f} m")
    else:
        st.error(plan.recommended.error)
    rows = []
    for option in plan.options:
        name = OPTION_STYLE[option.kind][3]
        if not option.found:
            rows.append(
                {
                    "Route": name,
                    "Distance": "—",
                    "Time": "—",
                    "Deepest water": "—",
                    "In water": "—",
                    "Over your limit": option.error,
                }
            )
            continue
        om = option.metrics
        rows.append(
            {
                "Route": name,
                "Distance": f"{om.length_m:,.0f} m" + (f" (+{om.detour_ratio:.0%})" if om.detour_ratio else ""),
                "Time": f"{om.travel_time_s / 60:.0f} min",
                "Deepest water": depth_text(om.max_depth_m),
                "In water": f"{om.wading_length_m:,.0f} m",
                "Over your limit": f"{om.segments_over_limit} section(s)" if om.segments_over_limit else "no",
            }
        )
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption(
        f"{plan.blocked_edges} network sections are over your limit in this scenario. "
        "Grey dashed: shortest ignoring flooding · orange dotted: shortest within your limit · "
        "purple: recommended (also weighs how close the water is to your limit)."
    )

    def describe(place: pl.Place, used) -> str:
        if place.method == "point":
            return "**selected point**"
        return f"**{place.label}** ({place.access_label(used)})"

    if route is not None:
        st.caption(
            f"From {describe(ends[START], route.origin.point)} → {describe(ends[DEST], route.destination.point)}"
        )
else:
    st.info(
        f"Set a start and a destination: search in the sidebar or click the map "
        f"(the next click sets the **{state.click_target.lower()}**)."
    )

out = st_folium(
    base_map(),
    key="map",
    height=640,
    use_container_width=True,
    feature_group_to_add=overlay,
    returned_objects=["last_clicked"],
)

click = out.get("last_clicked") if out else None
if click and click != state.last_click:
    state.last_click = click
    set_point(state.click_target, (click["lat"], click["lng"]), "map click")
    st.rerun()
