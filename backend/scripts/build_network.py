"""Build the Southbank routing graph, save it, and render an interactive map of it.

The primary network is OpenStreetMap's walking network. ``--source com`` builds the older
City of Melbourne network instead (kept for comparison).

Writes:
- data/processed/southbank_network.gpkg      (OSM; layers: nodes, edges, study_area)
- data/processed/southbank_network_com.gpkg  (with --source com)
- reports/network_map.html / reports/network_map_com.html

Run:  uv run python scripts/build_network.py [--source osm|com]
"""

from __future__ import annotations

import argparse
import json

import folium
import geopandas as gpd
import networkx as nx

from floodroute import config
from floodroute import places
from floodroute.network import JUNCTION, PARCEL_ACCESS, is_snappable, parcel_access_nodes, save_graph, to_gdfs
from floodroute.network import com_builder
from floodroute.network import osm_builder as ob
from floodroute.sources import com, osm

PROCESSED_DIR = config.PROCESSED_DIR
REPORT_DIR = config.REPORT_DIR
PLACES_PATH = config.PROCESSED_PLACES_PATH
OUTPUTS = {
    "osm": (config.PROCESSED_NETWORK_PATH, REPORT_DIR / "network_map.html"),
    "com": (config.PROCESSED_COM_NETWORK_PATH, REPORT_DIR / "network_map_com.html"),
}
SOURCES = {
    "osm": "OpenStreetMap walking network (© OpenStreetMap contributors, ODbL)",
    "com": "City of Melbourne Pedestrian Network (CC BY), 2019",
}
FADED = 0.3


def edge_class(d: dict) -> str:
    if d.get("is_parcel_link"):
        return "Parcel links (dead-end only)"
    if d.get("is_steps"):
        return "Steps"
    if d.get("is_crossing"):
        return "Crossings"
    if d.get("is_carriageway") and (d.get("cost_factor") or 1) > 1:
        return "Roads with a sidewalk alongside (avoided)"
    if d.get("is_carriageway"):
        return "Roads without a separate sidewalk"
    return "Footpaths"


STYLES = {  # class -> (colour, weight, dash)
    "Footpaths": ("#1f4e79", 3, None),
    "Crossings": ("#2ca02c", 4, None),
    "Steps": ("#d62728", 3, "2 4"),
    "Roads without a separate sidewalk": ("#8c6d31", 3, None),
    "Roads with a sidewalk alongside (avoided)": ("#888888", 2, "6 6"),
    "Parcel links (dead-end only)": ("#e6550d", 2, "4 4"),
}


def render_map(graph: nx.Graph, report_lines: list[str], source: str) -> folium.Map:
    nodes, edges = (g.to_crs(config.WGS84) for g in to_gdfs(graph))
    edges["length_m"] = edges["length_m"].round(1)
    edges["class"] = [edge_class(d) for *_, d in graph.edges(data=True)]
    for col in ("name", "highway"):
        if col not in edges:
            edges[col] = None
    area = gpd.GeoSeries([graph.graph["study_area"]], crs=graph.graph["crs"])
    ring = area.buffer(graph.graph["buffer_m"]).to_crs(config.WGS84)
    area = area.to_crs(config.WGS84)
    west, south, east, north = area.total_bounds
    fmap = folium.Map(location=[(south + north) / 2, (west + east) / 2], zoom_start=16,
                      tiles="OpenStreetMap", max_zoom=21)

    folium.GeoJson(ring, name=f"Routing buffer ({graph.graph['buffer_m']:.0f} m)",
                   style_function=lambda _: {"color": "#777", "weight": 1.5, "dashArray": "6 6",
                                             "fill": False}).add_to(fmap)
    tooltip = ["edge_id", "class", "highway", "name", "length_m"]
    for cls, (colour, weight, dash) in STYLES.items():
        sub = edges[edges["class"] == cls]
        if sub.empty:
            continue
        layer = folium.FeatureGroup(name=f"{cls} ({len(sub)})")
        for inside in (True, False):
            part = sub[sub.in_study_area == inside]
            if part.empty:
                continue
            opacity = 0.9 if inside else 0.9 * FADED
            folium.GeoJson(part[[*tooltip, "geometry"]],
                           style_function=lambda _, c=colour, w=weight, d=dash, o=opacity:
                           {"color": c, "weight": w, "opacity": o, "dashArray": d},
                           tooltip=folium.GeoJsonTooltip(tooltip)).add_to(layer)
        layer.add_to(fmap)

    parcel_stubs = parcel_access_nodes(graph)
    if parcel_stubs:
        parcels = folium.FeatureGroup(name=f"Parcels ({len(parcel_stubs)})")
        for pid, stubs in parcel_stubs.items():
            d = graph.nodes[stubs[0]]
            o = 0.9 if d["in_study_area"] else FADED
            p = nodes.geometry[nodes.node_id == stubs[0]].iloc[0]
            folium.CircleMarker([p.y, p.x], radius=5, color="#c51b8a", opacity=o, fill=True, fill_opacity=o,
                                tooltip=f"parcel {pid}<br>{len(stubs)} link(s)").add_to(parcels)
        parcels.add_to(fmap)

    dead_ends = folium.FeatureGroup(name="Dead ends", show=False)
    for r in nodes.itertuples():
        if graph.degree(r.node_id) == 1 and r.kind == JUNCTION:
            folium.CircleMarker([r.geometry.y, r.geometry.x], radius=3, color="#d62728", fill=True,
                                tooltip=f"node {r.node_id}").add_to(dead_ends)
    dead_ends.add_to(fmap)

    folium.GeoJson(area, name="Southbank boundary (CoM CLUE)",
                   style_function=lambda _: {"color": "#111", "weight": 3, "fill": False}).add_to(fmap)

    streets = edges[[is_snappable(d) for *_, d in graph.edges(data=True)]]
    inside_km = streets.loc[streets.in_study_area, "length_m"].sum() / 1000
    buffer_km = streets.loc[~streets.in_study_area, "length_m"].sum() / 1000
    panel = f"""
    <div style="position:fixed;bottom:24px;left:12px;z-index:9999;background:#fff;padding:10px 12px;
                border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,.3);font:12px/1.5 sans-serif;max-width:290px">
      <b>Southbank pedestrian network</b><br>
      Nodes {graph.number_of_nodes():,} &middot; Edges {graph.number_of_edges():,}<br>
      Walkable: {inside_km:.1f} km in Southbank + {buffer_km:.1f} km in buffer<br>
      <span style="color:#666">{'<br>'.join(report_lines)}</span><br>
      <span style="color:#666">Black line: CoM CLUE Southbank boundary. Grey dashed ring: {graph.graph['buffer_m']:.0f} m
      routing buffer (faded lines are routable, not selectable as start/end).</span><br>
      <span style="color:#666">Source: {SOURCES[source]}</span>
    </div>"""
    fmap.get_root().html.add_child(folium.Element(panel))
    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap


def build(source: str) -> tuple[nx.Graph, dict, list[str]]:
    area = com.load_study_area()
    if source == "osm":
        graph, report = ob.build_graph_from_osm(osm.load_walk_network(), config.METRIC_CRS, area, config.STUDY_AREA_BUFFER_M)
        lines = [f"Excluded: {report.indoor_removed} indoor, {report.private_removed} private, "
                 f"{report.use_sidepath_removed} use-sidepath way segments.",
                 f"{report.carriageway_with_sidewalk_penalised} road edges with a sidewalk alongside cost "
                 f"×{ob.CARRIAGEWAY_PENALTY:g} to walk along.",
                 f"{report.crossings} crossings, {report.steps} steps; {report.components_dropped} disconnected "
                 f"pieces ({report.nodes_dropped} nodes) dropped."]
    else:
        graph, report = com_builder.build_graph(com.load_pedestrian_network(), study_area=area, buffer_m=config.STUDY_AREA_BUFFER_M)
        lines = [f"Cleaned: {report.duplicates_removed} duplicates, {report.tjunction_splits} T-junction splits, "
                 f"{report.components_dropped} small components dropped. Parcels are terminal-only."]
    return graph, report.as_dict(), lines


def build_places() -> None:
    """Buildings and entrances in the routing CRS, with indoor-only entrances flagged."""
    buildings = gpd.read_file(config.OSM_BUILDINGS_PATH).to_crs(config.METRIC_CRS)
    entrances = gpd.read_file(config.OSM_ENTRANCES_PATH).to_crs(config.METRIC_CRS)
    entrances = places.mark_indoor_entrances(entrances, osm.load_walk_network())
    PLACES_PATH.unlink(missing_ok=True)
    buildings.to_file(PLACES_PATH, layer="buildings", driver="GPKG")
    entrances.to_file(PLACES_PATH, layer="entrances", driver="GPKG")
    print(f"places -> {PLACES_PATH.relative_to(config.REPO_ROOT)}: {len(buildings)} buildings, "
          f"{len(entrances)} entrances ({int(entrances.indoor_only.sum())} indoor-only)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", choices=sorted(OUTPUTS), default="osm")
    args = parser.parse_args()
    graph, report, lines = build(args.source)
    assert nx.is_connected(graph)
    assert all(graph.degree(n) == 1 for n, d in graph.nodes(data=True) if d["kind"] == PARCEL_ACCESS)
    gpkg, html = OUTPUTS[args.source]
    save_graph(graph, gpkg)
    html.parent.mkdir(parents=True, exist_ok=True)
    render_map(graph, lines, args.source).save(html)
    print(json.dumps(report, indent=2))
    print("graph ->", gpkg.relative_to(config.REPO_ROOT))
    print("map   ->", html.relative_to(config.REPO_ROOT))
    if args.source == "osm":
        build_places()


if __name__ == "__main__":
    main()
