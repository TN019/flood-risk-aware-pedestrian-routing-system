"""Build the routing graph G = (V, E) from the OpenStreetMap walking network.

Rules:

- Indoor ways are excluded (``highway=corridor`` or any ``indoor=*`` other than ``no``).
- Ways with ``foot=private|no`` are excluded.
- Car carriageways are excluded where pedestrians are told to use the side path
  (``foot=use_sidepath``).
- Carriageways that have a separately mapped sidewalk (``footway=sidewalk``) alongside most of
  their length are *kept* but get ``cost_factor = CARRIAGEWAY_PENALTY``. Removing them would cut
  the network, because many OSM sidewalks join the road only at junction nodes and crossings
  happen on the road itself. With the penalty, routes follow the sidewalk and only step onto the
  carriageway where they need to cross. Melbourne's OSM data rarely tags ``sidewalk=separate``,
  so "has a sidewalk alongside" is decided geometrically.
- Topology comes from OSM node ids: ways connect only where they share a node, so bridges
  and underpasses never join the paths they cross.
- The result is a simple undirected ``nx.Graph`` following ``floodroute.network.schema``.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

import geopandas as gpd
import networkx as nx
import osmnx as ox
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import substring

from floodroute.network.schema import JUNCTION

CARRIAGEWAYS = {
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
    "residential",
    "unclassified",
    "service",
    "road",
}
SIDEWALK_MATCH_M = 20.0  # a sidewalk within this distance runs "alongside" the carriageway
SIDEWALK_COVER_SHARE = 0.8  # share of carriageway length that must have a sidewalk alongside
CARRIAGEWAY_PENALTY = 3.0  # routing cost multiplier for walking along such a carriageway
EXCLUDED_FOOT = {"private", "no"}
SIMPLIFY_KEEP_DIFFERENT = ["highway", "footway", "name", "bridge", "tunnel", "layer", "level"]


@dataclass
class OsmBuildReport:
    input_nodes: int = 0
    input_edges: int = 0  # directed, unsimplified
    indoor_removed: int = 0
    private_removed: int = 0
    use_sidepath_removed: int = 0
    carriageway_with_sidewalk_penalised: int = 0
    outside_area_removed: int = 0
    self_loops_removed: int = 0
    parallel_edges_split: int = 0
    components_dropped: int = 0
    nodes_dropped: int = 0
    nodes: int = 0
    edges: int = 0
    crossings: int = 0
    steps: int = 0

    def as_dict(self) -> dict[str, int]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


def tag_values(value) -> list[str]:
    """OSM tag value(s) as a list of strings (osmnx gives scalars, lists or NaN)."""
    if value is None or (isinstance(value, float) and value != value):
        return []
    return [str(v) for v in value] if isinstance(value, list) else [str(value)]


def joined(value) -> str | None:
    vals = list(dict.fromkeys(tag_values(value)))
    return ";".join(vals) if vals else None


def _is_indoor(data: dict) -> bool:
    return "corridor" in tag_values(data.get("highway")) or any(v != "no" for v in tag_values(data.get("indoor")))


def build_graph_from_osm(
    osm: nx.MultiDiGraph,
    crs: str,
    study_area: BaseGeometry | None = None,
    buffer_m: float = 0.0,
    keep_all_components: bool = False,
) -> tuple[nx.Graph, OsmBuildReport]:
    """Build the routing graph from an *unsimplified* osmnx walk graph (any CRS)."""
    report = OsmBuildReport(input_nodes=osm.number_of_nodes(), input_edges=osm.number_of_edges())
    g = ox.project_graph(osm, to_crs=crs)
    _fill_geometry(g)

    drop = []
    for u, v, k, d in g.edges(keys=True, data=True):
        if _is_indoor(d):
            report.indoor_removed += 1
        elif set(tag_values(d.get("foot"))) & EXCLUDED_FOOT:
            report.private_removed += 1
        elif "use_sidepath" in tag_values(d.get("foot")):
            report.use_sidepath_removed += 1
        else:
            continue
        drop.append((u, v, k))
    g.remove_edges_from(drop)

    sidewalks = [d["geometry"] for *_, d in g.edges(keys=True, data=True) if "sidewalk" in tag_values(d.get("footway"))]
    near_sidewalk = gpd.GeoSeries(sidewalks).union_all().buffer(SIDEWALK_MATCH_M) if sidewalks else None
    for *_, d in g.edges(keys=True, data=True):
        d["is_carriageway"] = bool(set(tag_values(d.get("highway"))) & CARRIAGEWAYS)
        geom = d["geometry"]
        d["has_sidewalk_alongside"] = bool(
            d["is_carriageway"]
            and near_sidewalk is not None
            and geom.length > 0
            and geom.intersection(near_sidewalk).length / geom.length >= SIDEWALK_COVER_SHARE
        )

    if study_area is not None:
        keep_zone = study_area.buffer(buffer_m)
        drop = [(u, v, k) for u, v, k, d in g.edges(keys=True, data=True) if not d["geometry"].intersects(keep_zone)]
        report.outside_area_removed = len(drop)
        g.remove_edges_from(drop)

    g.remove_nodes_from([n for n in list(g.nodes) if g.degree(n) == 0])
    g = ox.simplify_graph(g, edge_attrs_differ=[*SIMPLIFY_KEEP_DIFFERENT, "has_sidewalk_alongside"])
    _fill_geometry(g)
    und = ox.convert.to_undirected(g)

    graph = nx.Graph(crs=crs, study_area=study_area, buffer_m=buffer_m, source="OpenStreetMap")
    next_mid = -1
    for u, v, d in und.edges(data=True):
        if u == v:
            report.self_loops_removed += 1
            continue
        for n in (u, v):
            if n not in graph:
                nd = und.nodes[n]
                graph.add_node(
                    n,
                    x=nd["x"],
                    y=nd["y"],
                    kind=JUNCTION,
                    osm_highway=joined(nd.get("highway")),
                    crossing=joined(nd.get("crossing")),
                )
        attrs = _edge_attrs(d)
        geom = _oriented(attrs["geometry"], und.nodes[u])
        if graph.has_edge(u, v):
            report.parallel_edges_split += 1
            mid = geom.interpolate(0.5, normalized=True)
            m, next_mid = next_mid, next_mid - 1
            graph.add_node(m, x=mid.x, y=mid.y, kind=JUNCTION, osm_highway=None, crossing=None)
            graph.add_edge(u, m, **{**attrs, "geometry": substring(geom, 0, 0.5, normalized=True)})
            graph.add_edge(m, v, **{**attrs, "geometry": substring(geom, 0.5, 1, normalized=True)})
        else:
            graph.add_edge(u, v, **{**attrs, "geometry": geom})

    comps = sorted(nx.connected_components(graph), key=len, reverse=True)
    for comp in comps[1:] if not keep_all_components else []:
        report.components_dropped += 1
        report.nodes_dropped += len(comp)
        graph.remove_nodes_from(comp)

    for i, (_, _, d) in enumerate(graph.edges(data=True)):
        d["edge_id"] = f"e{i}"
        d["length_m"] = d["geometry"].length
        d["in_study_area"] = study_area is None or d["geometry"].intersects(study_area)
    for _, d in graph.nodes(data=True):
        d["in_study_area"] = study_area is None or study_area.covers(Point(d["x"], d["y"]))
    report.nodes, report.edges = graph.number_of_nodes(), graph.number_of_edges()
    report.carriageway_with_sidewalk_penalised = sum(1 for *_, d in graph.edges(data=True) if d["cost_factor"] > 1)
    report.crossings = sum(1 for *_, d in graph.edges(data=True) if d["is_crossing"])
    report.steps = sum(1 for *_, d in graph.edges(data=True) if d["is_steps"])
    return graph, report


def _fill_geometry(g: nx.MultiDiGraph) -> None:
    for u, v, _k, d in g.edges(keys=True, data=True):
        if "geometry" not in d:
            d["geometry"] = LineString([(g.nodes[u]["x"], g.nodes[u]["y"]), (g.nodes[v]["x"], g.nodes[v]["y"])])


def _oriented(geom: LineString, start_node: dict) -> LineString:
    start = Point(start_node["x"], start_node["y"])
    if Point(geom.coords[0]).distance(start) <= Point(geom.coords[-1]).distance(start):
        return geom
    return LineString(geom.coords[::-1])


def _edge_attrs(d: dict) -> dict:
    highway = tag_values(d.get("highway"))
    return {
        "geometry": d["geometry"],
        "osmid": joined(d.get("osmid")),
        "highway": joined(d.get("highway")),
        "name": joined(d.get("name")),
        "is_steps": "steps" in highway,
        "is_crossing": "crossing" in tag_values(d.get("footway")) or "crossing" in tag_values(d.get("highway")),
        "is_bridge": any(v not in ("no",) for v in tag_values(d.get("bridge"))),
        "is_tunnel": any(v not in ("no",) for v in tag_values(d.get("tunnel"))),
        "is_carriageway": any(v is True or v == "True" for v in _as_list(d.get("is_carriageway"))),
        "cost_factor": CARRIAGEWAY_PENALTY
        if any(v is True or v == "True" for v in _as_list(d.get("has_sidewalk_alongside")))
        else 1.0,
    }


def _as_list(value) -> list:
    return value if isinstance(value, list) else [value]
