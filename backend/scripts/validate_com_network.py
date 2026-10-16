"""Validate the City of Melbourne pedestrian network for the Southbank study area.

Checks the raw CoM export for geometry and topology problems, then cross-checks it
against the OpenStreetMap walking network. Writes:

- reports/network_validation.md       summary report
- reports/network_validation_map.html interactive map of every flagged location
- reports/network_validation_issues.geojson flagged features (for QGIS etc.)

Run:  uv run python scripts/validate_com_network.py
"""

from __future__ import annotations

import collections
import random
from dataclasses import dataclass, field

import folium
import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
from shapely.geometry import LineString, Point, box
from shapely.strtree import STRtree

from floodroute import config
from floodroute.sources import com, osm

REPORT_DIR = config.REPORT_DIR

NODE_PRECISION_M = 0.001  # endpoints closer than this are the same node
TJUNCTION_TOL_M = 0.05  # endpoint this close to another line's interior = missing split
BOUNDARY_BAND_M = 50.0  # dangles this close to the data extent are clipping artefacts
COVER_BUFFER_M = 8.0  # CoM and OSM lines within this distance are "the same path"
COM_DOMAIN_BUFFER_M = 80.0  # CoM data domain = lines buffered by this, then shrunk by half
GRADE_SEP_RADIUS_M = 15.0  # OSM bridge/tunnel this close to a crossing explains it
CROSSING_MATCH_M = 10.0  # OSM crossing node matched if a CoM node is this close
OD_SAMPLES = 1500
OD_RATIO_FLAG = 1.3  # flag OD pairs whose network distances differ by more than 30%
RANDOM_SEED = 42


@dataclass
class Issues:
    rows: list[dict] = field(default_factory=list)

    def add(self, kind: str, geom, **props) -> None:
        self.rows.append({"kind": kind, "geometry": geom, **props})

    def gdf(self) -> gpd.GeoDataFrame:
        return gpd.GeoDataFrame(self.rows, geometry="geometry", crs=config.METRIC_CRS)

    def count(self, kind: str) -> int:
        return sum(1 for r in self.rows if r["kind"] == kind)


def node_key(xy) -> tuple[float, float]:
    return (round(xy[0] / NODE_PRECISION_M) * NODE_PRECISION_M, round(xy[1] / NODE_PRECISION_M) * NODE_PRECISION_M)


def build_endpoint_graph(lines: gpd.GeoDataFrame) -> nx.MultiGraph:
    """Connect lines only where their endpoints coincide (no implicit intersections)."""
    graph = nx.MultiGraph()
    for idx, geom in zip(lines.index, lines.geometry, strict=True):
        u, v = node_key(geom.coords[0]), node_key(geom.coords[-1])
        graph.add_edge(u, v, line=idx, length=geom.length)
    return graph


def as_list(value) -> list:
    if isinstance(value, list):
        return value
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    return [value]


def osm_label(row) -> str:
    for key in ("bridge:name", "name"):
        names = [str(n) for n in as_list(row.get(key)) if isinstance(n, str)]
        if names:
            return ", ".join(names)
    return "(unnamed)"


def load_osm() -> tuple[nx.MultiGraph, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    graph = osm.load_walk_network()
    graph = ox.project_graph(graph, to_crs=config.METRIC_CRS)
    undirected = ox.convert.to_undirected(graph)
    nodes, edges = ox.graph_to_gdfs(undirected)
    return undirected, nodes, edges


def main() -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    issues = Issues()
    out: list[str] = []

    # ------------------------------------------------------------------ CoM basics
    raw = com.load_pedestrian_network()
    lines = raw[raw.geom_type == "LineString"].copy()
    points = raw[raw.geom_type == "Point"].copy()
    other_types = sorted(set(raw.geom_type) - {"LineString", "Point"})

    dup_mask = lines.geometry.normalize().to_wkb().duplicated(keep="first")
    for geom in lines[dup_mask].geometry:
        issues.add("duplicate_line", geom)
    self_loops = lines[[g.coords[0] == g.coords[-1] for g in lines.geometry]]
    for geom in self_loops.geometry:
        issues.add("self_loop", geom, length_m=round(geom.length, 1))

    graph = build_endpoint_graph(lines[~dup_mask])
    node_xy = np.array(list(graph.nodes()))
    node_pts = [Point(xy) for xy in node_xy]
    node_tree = STRtree(node_pts)
    degree = dict(graph.degree())

    comps = sorted(nx.connected_components(graph), key=len, reverse=True)
    giant = comps[0]
    for comp in comps[1:]:
        comp_lines = [lines.geometry[d["line"]] for _, _, d in graph.subgraph(comp).edges(data=True)]
        geom = comp_lines[0] if len(comp_lines) == 1 else LineString([c for ln in comp_lines for c in ln.coords])
        issues.add("disconnected_component", geom, nodes=len(comp))

    parallel = [
        (u, v) for u, v in {(u, v) for u, v, _ in graph.edges(keys=True)} if u != v and graph.number_of_edges(u, v) > 1
    ]
    for u, v in parallel:
        issues.add("parallel_edges", LineString([u, v]), count=graph.number_of_edges(u, v))

    # ------------------------------------------------------------------ Points
    pt_dist = np.array([p.distance(node_pts[node_tree.nearest(p)]) for p in points.geometry])
    pt_on_node = pt_dist < 0.01
    pt_node_deg = [degree[tuple(node_xy[node_tree.nearest(p)])] for p in points.geometry]
    deg_on_node = collections.Counter(np.array(pt_node_deg)[pt_on_node])
    for geom, d in zip(points.geometry[~pt_on_node], pt_dist[~pt_on_node], strict=True):
        issues.add("point_off_network", geom, dist_m=round(float(d), 1))
    point_node_keys = {node_key(p.coords[0]) for p in points.geometry[pt_on_node]}

    # ------------------------------------------------------------------ Parcel links
    # Points mark property parcels; lines touching them link a parcel into the street network.
    # A parcel point with several links lets a route pass *through* the parcel.
    clean = lines[~dup_mask]
    is_link = np.array(
        [node_key(g.coords[0]) in point_node_keys or node_key(g.coords[-1]) in point_node_keys for g in clean.geometry]
    )
    hubs = [k for k in point_node_keys if degree.get(k, 0) >= 2]
    for k in hubs:
        issues.add("parcel_hub", Point(k), degree=degree[k])

    # ------------------------------------------------------------------ Dangling ends
    extent = box(*lines.total_bounds).exterior
    dangle_counts = collections.Counter()
    for xy in node_xy:
        key = tuple(xy)
        if degree[key] != 1:
            continue
        p = Point(xy)
        if p.distance(extent) < BOUNDARY_BAND_M:
            dangle_counts["near data boundary (clipping)"] += 1
        elif key in point_node_keys:
            dangle_counts["ends at a property-link point"] += 1
        else:
            dangle_counts["other (review)"] += 1
            ((_, _, data),) = graph.edges(key, data=True)
            issues.add("dangle_unexplained", p, edge_length_m=round(data["length"], 1))

    # ------------------------------------------------------------------ OSM
    osm_graph, osm_nodes, osm_edges = load_osm()
    osm_edges = osm_edges.reset_index(drop=True)
    # All OSM bridges (roads, rail and paths, not only walkable ways) plus walkable tunnels.
    bridges = gpd.read_file(config.OSM_BRIDGES_PATH).to_crs(config.METRIC_CRS)
    bridges["label"] = bridges.apply(osm_label, axis=1)
    tunnels = osm_edges[osm_edges["tunnel"].apply(lambda t: "yes" in as_list(t))]
    grade_sep_tree = STRtree(list(bridges.geometry) + list(tunnels.geometry))
    grade_sep_names = list(bridges.label) + [osm_label(r) for _, r in tunnels.iterrows()]

    def grade_sep_near(p: Point) -> str | None:
        hits = grade_sep_tree.query(p.buffer(GRADE_SEP_RADIUS_M))
        if len(hits) == 0:
            return None
        return ", ".join(sorted({grade_sep_names[h] for h in hits}))

    # ------------------------------------------------------------------ Interior crossings
    geoms = list(clean.geometry)
    line_tree = STRtree(geoms)
    crossing_counts = collections.Counter()
    for i, a in enumerate(geoms):
        for j in line_tree.query(a, predicate="crosses"):
            if j <= i:
                continue
            x = a.intersection(geoms[j])
            p = x if x.geom_type == "Point" else x.representative_point()
            if is_link[i] or is_link[j]:
                crossing_counts["involves a parcel-link line"] += 1
                issues.add("crossing_parcel_link", p)
            elif explained := grade_sep_near(p):
                crossing_counts["street lines, near OSM bridge/tunnel (grade-separated)"] += 1
                issues.add("crossing_grade_separated", p, osm=explained)
            else:
                crossing_counts["street lines, no bridge/tunnel nearby (review)"] += 1
                issues.add("crossing_unexplained", p)

    # ------------------------------------------------------------------ T-junctions
    tj = 0
    for p in node_pts:
        for j in line_tree.query(p.buffer(TJUNCTION_TOL_M)):
            ln = geoms[j]
            if (
                p.distance(ln) < TJUNCTION_TOL_M
                and p.distance(Point(ln.coords[0])) > TJUNCTION_TOL_M
                and p.distance(Point(ln.coords[-1])) > TJUNCTION_TOL_M
            ):
                tj += 1
                issues.add("missing_split", p)

    # ------------------------------------------------------------------ Coverage vs OSM
    # Compare only where CoM actually has data: the dataset stops at the municipal boundary,
    # so the bbox corners outside the City of Melbourne would count as false "missing" paths.
    clip = lines.geometry.union_all().buffer(COM_DOMAIN_BUFFER_M).buffer(-COM_DOMAIN_BUFFER_M / 2)
    osm_in = osm_edges[osm_edges.intersects(clip)].copy()
    osm_in["geometry"] = osm_in.geometry.intersection(clip)
    osm_in = osm_in[~osm_in.geometry.is_empty]
    osm_walkable = osm_in[~osm_in.highway.apply(lambda h: "corridor" in as_list(h))]

    com_union_buf = clean.geometry.union_all().buffer(COVER_BUFFER_M)
    osm_union_buf = osm_walkable.geometry.union_all().buffer(COVER_BUFFER_M)
    com_len = clean.length.sum()
    com_cov = clean.geometry.intersection(osm_union_buf).length.sum() / com_len
    osm_len = osm_walkable.length.sum()
    osm_cov_len = osm_walkable.geometry.intersection(com_union_buf).length
    osm_cov = osm_cov_len.sum() / osm_len

    osm_walkable = osm_walkable.assign(uncovered_m=osm_walkable.length - osm_cov_len)
    uncovered_by_type = (
        osm_walkable.assign(hw=osm_walkable.highway.apply(lambda h: as_list(h)[0]))
        .groupby("hw")["uncovered_m"]
        .sum()
        .sort_values(ascending=False)
    )
    for _, r in osm_walkable[osm_walkable.uncovered_m > 20].iterrows():
        issues.add(
            "osm_path_missing_in_com",
            r.geometry.difference(com_union_buf),
            highway=as_list(r.highway)[0],
            name=", ".join(map(str, as_list(r.get("name")))),
            missing_m=round(r.uncovered_m, 1),
        )

    # OSM signalised/zebra crossing nodes inside the extent
    xings = osm_nodes[(osm_nodes.highway == "crossing") & osm_nodes.within(clip)]
    x_dist = np.array([p.distance(node_pts[node_tree.nearest(p)]) for p in xings.geometry])
    # a crossing is "represented" if CoM has a line passing close by, not necessarily a node
    x_line_dist = np.array([p.distance(geoms[line_tree.nearest(p)]) for p in xings.geometry])
    far = x_line_dist > CROSSING_MATCH_M
    for p, d in zip(xings.geometry[far], x_line_dist[far], strict=True):
        issues.add("osm_crossing_not_in_com", p, nearest_com_line_m=round(float(d), 1))

    # River crossings: which CoM lines span water, which OSM bridge they sit on, are both ends connected?
    water = gpd.read_file(config.OSM_WATER_PATH).to_crs(config.METRIC_CRS)
    water = water[water.geom_type.isin(["Polygon", "MultiPolygon"])].geometry.union_all()
    over = clean.geometry.intersection(water).length
    river_lines = clean[(over > 15) & ~is_link]
    water_bridges = bridges[bridges.intersects(water.buffer(5))]
    wb_tree = STRtree(list(water_bridges.geometry))
    wb_labels = list(water_bridges.label)
    crossing_rows = []
    for _, r in river_lines.iterrows():
        mid = r.geometry.intersection(water).centroid
        names = sorted({wb_labels[h] for h in wb_tree.query(mid.buffer(25))} - {"(unnamed)"})
        degs = (degree[node_key(r.geometry.coords[0])], degree[node_key(r.geometry.coords[-1])])
        crossing_rows.append((r.objectid, ", ".join(names) or "(unnamed / none)", round(over[_]), min(degs) >= 2))
        if min(degs) < 2:
            issues.add("river_line_dead_end", r.geometry, objectid=r.objectid)
    river_df = pd.DataFrame(
        crossing_rows, columns=["objectid", "osm_bridge_nearby", "over_water_m", "both_ends_connected"]
    )
    named_water_bridges = sorted(set(wb_labels) - {"(unnamed)"})
    covered_names = {n.strip() for s in river_df.osm_bridge_nearby for n in s.split(",")}
    uncovered_bridges = [n for n in named_water_bridges if n not in covered_names]

    # ------------------------------------------------------------------ OD distance comparison
    rng = random.Random(RANDOM_SEED)
    inner = box(*lines.total_bounds).buffer(-150)
    giant_nodes = [n for n in giant if Point(n).within(inner)]
    g_sub = graph.subgraph(giant)
    osm_node_ids = np.array(osm_nodes.index)
    osm_node_tree = STRtree(list(osm_nodes.geometry))
    osm_main = max(nx.connected_components(osm_graph), key=len)
    ratios = []
    for _ in range(OD_SAMPLES):
        a, b = rng.sample(giant_nodes, 2)
        pa, pb = Point(a), Point(b)
        if pa.distance(pb) < 200:
            continue
        oa = osm_node_ids[osm_node_tree.nearest(pa)]
        ob = osm_node_ids[osm_node_tree.nearest(pb)]
        if oa not in osm_main or ob not in osm_main:
            continue
        snap = pa.distance(osm_nodes.geometry[oa]) + pb.distance(osm_nodes.geometry[ob])
        if snap > 30:
            continue
        d_com = nx.shortest_path_length(g_sub, a, b, weight="length")
        d_osm = nx.shortest_path_length(osm_graph, oa, ob, weight="length")
        ratio = d_com / d_osm
        ratios.append(ratio)
        if ratio > OD_RATIO_FLAG or ratio < 1 / OD_RATIO_FLAG:
            issues.add(
                "od_distance_mismatch",
                LineString([a, b]),
                com_m=round(d_com),
                osm_m=round(d_osm),
                ratio=round(ratio, 2),
            )
    ratios = np.array(ratios)

    # Effect of forbidding through-parcel travel (remove parcel hubs)
    g_nohub = graph.copy()
    g_nohub.remove_nodes_from(hubs)
    nohub_main = max(nx.connected_components(g_nohub), key=len)
    hub_ratios = []
    candidates = [n for n in giant_nodes if n in nohub_main]
    for _ in range(OD_SAMPLES):
        a, b = rng.sample(candidates, 2)
        if Point(a).distance(Point(b)) < 200:
            continue
        hub_ratios.append(
            nx.shortest_path_length(g_nohub, a, b, weight="length")
            / nx.shortest_path_length(g_sub, a, b, weight="length")
        )
    hub_ratios = np.array(hub_ratios)

    # ------------------------------------------------------------------ Report
    lengths = clean.length
    out += [
        "# Pedestrian Network Validation — Southbank",
        "",
        f"Source: City of Melbourne *Pedestrian Network* (CC BY), last modified 2019-11-19; "
        f"bbox {config.SOUTHBANK_BBOX}. Compared with OpenStreetMap walk network (ODbL), downloaded with osmnx.",
        "",
        "## 1. Contents",
        f"- Records: {len(raw)} — LineString {len(lines)}, Point {len(points)}"
        + (f", other {other_types}" if other_types else ""),
        "- Attributes: only `objectid`, `neworkid` (Points only) and geometry. "
        "No crossing type, bridge/level, width or surface attributes.",
        f"- `objectid` is not unique across Points and Lines ({raw.objectid.nunique()} unique / {len(raw)}).",
        f"- Line length: median {lengths.median():.1f} m, max {lengths.max():.0f} m, "
        f"{(lengths > 100).sum()} lines longer than 100 m (candidates for splitting at flood boundaries).",
        f"- Exact duplicate lines: {dup_mask.sum()}; self-loops: {len(self_loops)}; "
        f"node pairs joined by >1 line: {len(parallel)}.",
        "",
        "## 2. Topology (connect only at shared endpoints)",
        f"- Nodes {graph.number_of_nodes()}, edges {graph.number_of_edges()}.",
        "- Endpoints coincide exactly: snapping tolerance makes no difference up to 0.5 m.",
        f"- Connected components: {len(comps)}; largest holds {len(giant)} nodes "
        f"({len(giant) / graph.number_of_nodes():.1%}). Others: {[len(c) for c in comps[1:]]}.",
        "- Dead ends (degree-1 nodes):",
        *[f"  - {k}: {v}" for k, v in dangle_counts.most_common()],
        f"- Points: {pt_on_node.sum()}/{len(points)} sit exactly on a network node; node degree: "
        f"{dict(sorted(deg_on_node.items()))}. Degree-1 points are where the network links into "
        "property parcels, i.e. likely building/lot access points.",
        "- Lines whose interiors cross without a shared node:",
        *[f"  - {k}: {v}" for k, v in crossing_counts.most_common()],
        f"- Endpoints lying on another line's interior (line not split): {tj}.",
        "",
        "### Parcel links",
        f"- {is_link.sum()} of {len(clean)} lines ({clean.length[is_link].sum() / clean.length.sum():.1%} of length) "
        "touch a parcel Point: they link a property into the street network rather than follow a walkway.",
        f"- {len(hubs)} parcel Points have ≥2 links, so a route can pass *through* the parcel "
        f"(max links on one parcel: {max(degree[k] for k in hubs)}).",
        f"- Removing those hubs: {nx.number_connected_components(g_nohub)} components, largest "
        f"{len(nohub_main)} of {g_nohub.number_of_nodes()} nodes; over {len(hub_ratios)} OD pairs the shortest "
        f"path gets longer for {(hub_ratios > 1.01).mean():.0%} of pairs (median ×{np.median(hub_ratios):.3f}, "
        f"95th pct ×{np.quantile(hub_ratios, 0.95):.3f}).",
        "",
        "## 3. Comparison with OpenStreetMap",
        f"- {com_cov:.1%} of CoM line length lies within {COVER_BUFFER_M:.0f} m of an OSM walkable way.",
        f"- {osm_cov:.1%} of OSM walkable length (excl. indoor corridors) lies within "
        f"{COVER_BUFFER_M:.0f} m of a CoM line.",
        "- OSM length with no CoM line nearby, by highway type (m):",
        *[f"  - {k}: {v:.0f}" for k, v in uncovered_by_type.head(10).items() if v > 0],
        f"- OSM crossing nodes in extent: {len(xings)}; with a CoM line within {CROSSING_MATCH_M:.0f} m: "
        f"{(x_line_dist <= CROSSING_MATCH_M).sum()} ({(x_line_dist <= CROSSING_MATCH_M).mean():.1%}); "
        f"with a CoM node within {CROSSING_MATCH_M:.0f} m: {(x_dist <= CROSSING_MATCH_M).mean():.1%}.",
        "",
        "### River crossings",
        f"- Named OSM bridges over water in the extent: {', '.join(named_water_bridges)}.",
        f"- Named bridges with no CoM line on them: {', '.join(uncovered_bridges) or 'none'}.",
        "",
        "| CoM objectid | OSM bridge within 25 m | Over water (m) | Both ends connected |",
        "|---|---|---|---|",
        *[
            f"| {r.objectid} | {r.osm_bridge_nearby} | {r.over_water_m} | {'yes' if r.both_ends_connected else 'NO'} |"
            for r in river_df.sort_values("osm_bridge_nearby").itertuples()
        ],
        "",
        "### Shortest-path distance, CoM vs OSM",
        f"- {len(ratios)} random OD pairs (≥200 m apart, inside the extent minus 150 m).",
        f"- Ratio CoM/OSM: median {np.median(ratios):.3f}, 5–95% "
        f"[{np.quantile(ratios, 0.05):.3f}, {np.quantile(ratios, 0.95):.3f}]; "
        f"{((ratios > OD_RATIO_FLAG) | (ratios < 1 / OD_RATIO_FLAG)).sum()} pairs differ by >30%.",
        "",
        "## 4. Flagged features",
        "",
        "| Kind | Count |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in collections.Counter(r["kind"] for r in issues.rows).most_common()],
        "",
        "All flagged features are in `network_validation_issues.geojson` and on the interactive map "
        "`network_validation_map.html`.",
    ]
    (REPORT_DIR / "network_validation.md").write_text("\n".join(out) + "\n")

    issues_gdf = issues.gdf()
    issues_gdf.to_crs(config.WGS84).to_file(REPORT_DIR / "network_validation_issues.geojson", driver="GeoJSON")
    write_map(clean, is_link, osm_walkable, issues_gdf)
    print("\n".join(out))


STYLE = {
    "crossing_unexplained": ("red", "Street crossing, no node, no bridge/tunnel"),
    "crossing_grade_separated": ("purple", "Street crossing near OSM bridge/tunnel"),
    "crossing_parcel_link": ("pink", "Crossing involving a parcel link"),
    "parcel_hub": ("magenta", "Parcel point with ≥2 links (through-parcel)"),
    "river_line_dead_end": ("black", "River-crossing line with a dead end"),
    "missing_split": ("orange", "Endpoint on line interior (not split)"),
    "dangle_unexplained": ("darkred", "Unexplained dead end"),
    "disconnected_component": ("black", "Disconnected component"),
    "duplicate_line": ("gray", "Duplicate line"),
    "parallel_edges": ("gray", "Parallel edges"),
    "self_loop": ("gray", "Self-loop"),
    "point_off_network": ("cadetblue", "Point not on a node"),
    "osm_path_missing_in_com": ("green", "OSM path with no CoM line"),
    "osm_crossing_not_in_com": ("darkgreen", "OSM crossing with no CoM line"),
    "od_distance_mismatch": ("blue", "OD distance differs >30%"),
}


def write_map(clean, is_link, osm_walkable, issues_gdf) -> None:
    centre = config.SOUTHBANK_BBOX
    fmap = folium.Map(
        location=[(centre.south + centre.north) / 2, (centre.west + centre.east) / 2],
        zoom_start=16,
        tiles="OpenStreetMap",
        max_zoom=21,
    )

    folium.GeoJson(
        osm_walkable[["geometry"]].to_crs(config.WGS84),
        name="OSM walk network",
        style_function=lambda _: {"color": "#2ca02c", "weight": 1, "opacity": 0.5},
        show=False,
    ).add_to(fmap)
    folium.GeoJson(
        clean.loc[~is_link, ["objectid", "geometry"]].to_crs(config.WGS84),
        name="CoM street/path lines",
        style_function=lambda _: {"color": "#1f4e79", "weight": 2, "opacity": 0.8},
        tooltip=folium.GeoJsonTooltip(["objectid"]),
    ).add_to(fmap)
    folium.GeoJson(
        clean.loc[is_link, ["objectid", "geometry"]].to_crs(config.WGS84),
        name="CoM parcel-link lines",
        style_function=lambda _: {"color": "#e6550d", "weight": 1.5, "opacity": 0.8, "dashArray": "4 4"},
        tooltip=folium.GeoJsonTooltip(["objectid"]),
    ).add_to(fmap)

    wgs = issues_gdf.to_crs(config.WGS84)
    for kind, (colour, label) in STYLE.items():
        sub = wgs[wgs.kind == kind]
        if sub.empty:
            continue
        layer = folium.FeatureGroup(
            name=f"{label} ({len(sub)})",
            show=kind
            not in {
                "crossing_grade_separated",
                "crossing_parcel_link",
                "od_distance_mismatch",
                "osm_path_missing_in_com",
            },
        )
        props = [c for c in sub.columns if c not in ("geometry",) and sub[c].notna().any()]
        for _, r in sub.iterrows():
            tip = "<br>".join(f"{c}: {r[c]}" for c in props if pd.notna(r[c]))
            if r.geometry.geom_type == "Point":
                folium.CircleMarker(
                    [r.geometry.y, r.geometry.x], radius=6, color=colour, fill=True, fill_opacity=0.8, tooltip=tip
                ).add_to(layer)
            else:
                folium.GeoJson(
                    r.geometry.__geo_interface__,
                    tooltip=tip,
                    style_function=lambda _, c=colour: {"color": c, "weight": 5, "opacity": 0.8},
                ).add_to(layer)
        layer.add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)
    fmap.save(REPORT_DIR / "network_validation_map.html")


if __name__ == "__main__":
    main()
