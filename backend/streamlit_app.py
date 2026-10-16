"""Interim Streamlit map UI for the routing engine, until the web frontend replaces it.

Shortest walking route; flood conditions are not applied yet.

Run (from backend/):  uv run streamlit run streamlit_app.py
"""

from __future__ import annotations

import folium
import geopandas as gpd
import streamlit as st
from pyproj import Transformer
from shapely.geometry import Point
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

from floodroute import config
from floodroute import places as pl
from floodroute.network import is_snappable, load_graph, to_gdfs
from floodroute.routing import Router, RoutingError
from floodroute.sources import geocoding as geocode

GRAPH_PATH = config.PROCESSED_NETWORK_PATH
PLACES_PATH = config.PROCESSED_PLACES_PATH
START, DEST = "Start", "Destination"
CHOOSE, CURRENT = "A point I choose", "My current location"

NETWORK_COLOUR = "#4a6f94"
ROUTE_COLOUR = "#7b2cbf"
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
    return pl.PlaceResolver(gpd.read_file(PLACES_PATH, layer="buildings"),
                            gpd.read_file(PLACES_PATH, layer="entrances"), load_router().footpaths)


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
    folium.GeoJson(layers["ring"], style_function=lambda _: {"color": "#777", "weight": 1.5, "dashArray": "6 6",
                                                              "fill": False}, interactive=False).add_to(fmap)
    folium.GeoJson(layers["avoided_roads"],
                   style_function=lambda _: {"color": "#999", "weight": 1.5, "opacity": 0.5, "dashArray": "4 6"},
                   interactive=False).add_to(fmap)
    folium.GeoJson(layers["buffer_streets"],
                   style_function=lambda _: {"color": NETWORK_COLOUR, "weight": 2, "opacity": 0.3},
                   interactive=False).add_to(fmap)
    folium.GeoJson(layers["area_streets"],
                   style_function=lambda _: {"color": NETWORK_COLOUR, "weight": 2.5, "opacity": 0.8},
                   interactive=False).add_to(fmap)
    folium.GeoJson(layers["area"], style_function=lambda _: {"color": "#111", "weight": 3, "fill": False},
                   interactive=False).add_to(fmap)
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
    latlon, footprint, label = (state.start, state.start_fp, state.start_label) if which == START else \
        (state.dest, state.dest_fp, state.dest_label)
    role = pl.ORIGIN if which == START else pl.DESTINATION
    return load_places().resolve(to_point(latlon), label or "chosen point", to_metric_geom(footprint), role)


# --------------------------------------------------------------------------- state

state = st.session_state
for key, default in {"start": None, "dest": None, "start_src": None, "dest_src": None,
                     "start_fp": None, "dest_fp": None, "start_label": None, "dest_label": None,
                     "click_target": START, "last_click": None}.items():
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
    query = st.text_input(f"Search {which.lower()}", key=f"q_{which}",
                          placeholder="e.g. Eureka Tower, 1 City Road")
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
    choice = st.selectbox("Matches", range(len(places)), format_func=lambda i: labels[i][:80],
                          key=f"pick_{which}", label_visibility="collapsed")
    if st.button(f"Use as {which.lower()}", key=f"use_{which}", use_container_width=True):
        hit = places[choice]
        set_point(which, (hit.lat, hit.lon), "search", hit.footprint, hit.label.split(",")[0])
        st.rerun()


# --------------------------------------------------------------------------- sidebar

with st.sidebar:
    st.header("Southbank Routing")
    st.caption("Shortest walking route on the OpenStreetMap walking network (indoor corridors excluded; "
               "routes prefer sidewalks over walking along roads). Flood conditions are not applied yet.")

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
                st.warning(f"Your location is {km:.1f} km outside Southbank. "
                           "Click the map to set a simulated current location instead.")
        else:
            st.warning("Location unavailable (permission denied or not supported). "
                       "Click the map to set a simulated current location instead.")
    if mode == CHOOSE:
        search_box(START)
    search_box(DEST)

    st.divider()
    options = [DEST] if gps_ok else [START, DEST]
    if "next_click_target" in state:
        state.click_target = state.pop("next_click_target")
    if state.click_target not in options:
        state.click_target = DEST
    st.radio("A map click sets the", options, key="click_target", horizontal=True)

    for label, latlon, src in ((START, state.start, state.start_src), (DEST, state.dest, state.dest_src)):
        st.markdown(f"**{label}:** " + (f"{latlon[0]:.5f}, {latlon[1]:.5f} · {src}" if latlon else "not set"))
    if st.button("Clear points", use_container_width=True):
        for key in ("start", "dest", "start_src", "dest_src", "start_fp", "dest_fp", "start_label", "dest_label"):
            state[key] = None
        state.click_target = START
        st.rerun()


# --------------------------------------------------------------------------- route + map

router = load_router()
route, error, ends = None, None, {}
if state.start and state.dest:
    if not (in_southbank(state.start) and in_southbank(state.dest)):
        error = "Start and destination must both be inside Southbank (the black boundary)."
    else:
        ends = {START: resolve(START), DEST: resolve(DEST)}
        try:
            route = router.route(ends[START].access_points, ends[DEST].access_points)
        except RoutingError as exc:
            error = str(exc)

overlay = folium.FeatureGroup(name="route")
for which, place in ends.items():  # the building a start/destination resolved to, and its usable doors
    colour = START_COLOUR if which == START else DEST_COLOUR
    if place.building is not None:
        folium.GeoJson(gpd.GeoSeries([place.building], crs=config.METRIC_CRS).to_crs(config.WGS84).__geo_interface__,
                       style_function=lambda _, c=colour: {"color": c, "weight": 2, "fillOpacity": 0.12},
                       tooltip=place.label).add_to(overlay)
        for a in place.access:
            folium.CircleMarker(to_latlon(a.point), radius=4, color=colour, fill=True, fill_opacity=0.6,
                                tooltip=f"{place.label}: {a.label}").add_to(overlay)
if route is not None:
    folium.PolyLine([to_latlon(Point(c)) for c in route.geometry.coords], color=ROUTE_COLOUR, weight=7,
                    opacity=0.9, tooltip=f"{route.length_m:.0f} m").add_to(overlay)
    for snap in (route.origin, route.destination):  # short walk between the door/point and the footpath
        folium.PolyLine([to_latlon(snap.point), to_latlon(snap.snapped)], color=ROUTE_COLOUR, weight=3,
                        dash_array="4 6").add_to(overlay)
for which, colour in ((START, START_COLOUR), (DEST, DEST_COLOUR)):
    latlon = state.start if which == START else state.dest
    if route is not None:  # mark the door actually used rather than the middle of the building
        latlon = to_latlon((route.origin if which == START else route.destination).point)
    if latlon:
        folium.Marker(latlon, tooltip=which, icon=folium.Icon(color=colour, icon="flag" if which == DEST else "user",
                                                              prefix="fa")).add_to(overlay)

if error:
    st.error(error)
elif route is not None:
    c1, c2, c3 = st.columns(3)
    c1.metric("Walking distance", f"{route.length_m:,.0f} m")
    c2.metric("Estimated time", f"{route.travel_time_s / 60:.0f} min")
    c3.metric("Network edges used", len(route.edge_ids))
    def describe(place: pl.Place, used) -> str:
        if place.method == "point":
            return "**selected point**"
        return f"**{place.label}** ({place.access_label(used)})"

    st.caption(f"From {describe(ends[START], route.origin.point)} → "
               f"{describe(ends[DEST], route.destination.point)}")
else:
    st.info(f"Set a start and a destination: search in the sidebar or click the map "
            f"(the next click sets the **{state.click_target.lower()}**).")

out = st_folium(base_map(), key="map", height=640, use_container_width=True,
                feature_group_to_add=overlay, returned_objects=["last_clicked"])

click = out.get("last_clicked") if out else None
if click and click != state.last_click:
    state.last_click = click
    set_point(state.click_target, (click["lat"], click["lng"]), "map click")
    st.rerun()
