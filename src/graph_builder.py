"""Build the routing graph G = (V, E) from the CoM pedestrian network.

Design rules (see reports/network_validation.md for the evidence behind them):

- Lines connect only where their endpoints coincide. Crossing geometry never creates a
  junction, so bridges and underpasses stay separate.
- Exact duplicate lines and self-loops are dropped.
- An endpoint lying on another line's interior (a digitising T-junction) splits that line.
- CoM Point records mark property parcels. Parcel points are terminal-only: a route may start,
  end or shelter at a parcel but never pass through it. Each link into a parcel therefore gets
  its own degree-1 ``parcel_access`` node; all of them share the parcel's ``parcel_id``.
- The result is a simple undirected ``nx.Graph``: parallel lines get a midpoint node.
- Optionally, only lines touching the study area plus a buffer are kept. Nodes and edges carry
  ``in_study_area`` so origins/destinations can be limited to the study area itself while
  routes may still detour through the buffer.
- Only the largest connected component is kept.
"""

from __future__ import annotations

import collections
import itertools
from dataclasses import dataclass, fields
from pathlib import Path

import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import substring
from shapely.strtree import STRtree

NODE_PRECISION_M = 0.001  # endpoints closer than this are the same node
TJUNCTION_TOL_M = 0.05  # endpoint this close to another line's interior splits that line

JUNCTION = "junction"
PARCEL_ACCESS = "parcel_access"


@dataclass
class BuildReport:
    input_lines: int = 0
    input_points: int = 0
    lines_outside_area: int = 0
    duplicates_removed: int = 0
    self_loops_removed: int = 0
    tjunction_splits: int = 0
    parcel_hubs_split: int = 0
    parallel_edges_split: int = 0
    components_dropped: int = 0
    nodes_dropped: int = 0
    nodes: int = 0
    edges: int = 0
    parcels: int = 0

    def as_dict(self) -> dict[str, int]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


def node_key(xy) -> tuple[float, float]:
    return (round(xy[0] / NODE_PRECISION_M) * NODE_PRECISION_M,
            round(xy[1] / NODE_PRECISION_M) * NODE_PRECISION_M)


# ---------------------------------------------------------------------------- cleaning

def clean_lines(lines: gpd.GeoDataFrame, report: BuildReport) -> gpd.GeoDataFrame:
    """Drop duplicates and self-loops, then split lines at T-junctions."""
    lines = lines[["objectid", "geometry"]].reset_index(drop=True)
    dup = lines.geometry.normalize().to_wkb().duplicated(keep="first")
    report.duplicates_removed = int(dup.sum())
    lines = lines[~dup]
    loop = lines.geometry.apply(lambda g: node_key(g.coords[0]) == node_key(g.coords[-1]))
    report.self_loops_removed = int(loop.sum())
    lines = lines[~loop].reset_index(drop=True)
    return split_at_tjunctions(lines, report)


def split_at_tjunctions(lines: gpd.GeoDataFrame, report: BuildReport) -> gpd.GeoDataFrame:
    geoms = list(lines.geometry)
    tree = STRtree(geoms)
    endpoints = {node_key(c): c for g in geoms for c in (g.coords[0], g.coords[-1])}
    cuts: dict[int, list[tuple[float, tuple]]] = collections.defaultdict(list)
    for xy in endpoints.values():
        p = Point(xy)
        for j in tree.query(p.buffer(TJUNCTION_TOL_M)):
            ln = geoms[j]
            if (p.distance(ln) < TJUNCTION_TOL_M
                    and p.distance(Point(ln.coords[0])) > TJUNCTION_TOL_M
                    and p.distance(Point(ln.coords[-1])) > TJUNCTION_TOL_M):
                cuts[j].append((ln.project(p), tuple(xy)))

    rows = []
    for j, (oid, ln) in enumerate(zip(lines.objectid, geoms)):
        if j not in cuts:
            rows.append((oid, ln))
            continue
        report.tjunction_splits += len(cuts[j])
        bounds = [(0.0, ln.coords[0]), *sorted(cuts[j]), (ln.length, ln.coords[-1])]
        for (d0, xy0), (d1, xy1) in itertools.pairwise(bounds):
            if d1 - d0 < NODE_PRECISION_M:
                continue
            coords = list(substring(ln, d0, d1).coords)
            coords[0], coords[-1] = xy0, xy1  # snap so the pieces share the exact node
            rows.append((oid, LineString(coords)))
    return gpd.GeoDataFrame(rows, columns=["objectid", "geometry"], geometry="geometry", crs=lines.crs)


# ---------------------------------------------------------------------------- graph

def build_graph(raw: gpd.GeoDataFrame, study_area: BaseGeometry | None = None,
                buffer_m: float = 0.0) -> tuple[nx.Graph, BuildReport]:
    """Build the routing graph from a raw CoM export (LineStrings + parcel Points), metric CRS.

    With ``study_area``, lines that do not touch ``study_area`` buffered by ``buffer_m`` are
    dropped. Lines crossing the buffer edge are kept whole rather than cut.
    """
    report = BuildReport()
    lines = raw[raw.geom_type == "LineString"]
    points = raw[raw.geom_type == "Point"]
    report.input_lines, report.input_points = len(lines), len(points)
    if study_area is not None:
        keep = lines.intersects(study_area.buffer(buffer_m))
        report.lines_outside_area = int((~keep).sum())
        lines = lines[keep]

    lines = clean_lines(lines, report)

    # Parcel id per node location. A few Points do not sit on the network; they are ignored.
    parcel_at = {node_key(p.coords[0]): str(pid) for p, pid in zip(points.geometry, points.neworkid)}

    node_ids: dict[tuple, int] = {}
    nodes: dict[int, dict] = {}

    def junction(xy) -> int:
        key = node_key(xy)
        if key not in node_ids:
            node_ids[key] = len(nodes)
            nodes[node_ids[key]] = {"x": key[0], "y": key[1], "kind": JUNCTION, "parcel_id": None}
        return node_ids[key]

    def parcel_stub(xy, parcel_id: str) -> int:
        nid = len(nodes)
        key = node_key(xy)
        nodes[nid] = {"x": key[0], "y": key[1], "kind": PARCEL_ACCESS, "parcel_id": parcel_id}
        return nid

    # Every line touching a parcel gets its own stub node at the parcel end.
    links_per_parcel = collections.Counter()
    edges = []
    for oid, geom in zip(lines.objectid, lines.geometry):
        ends = []
        for xy in (geom.coords[0], geom.coords[-1]):
            pid = parcel_at.get(node_key(xy))
            if pid is None:
                ends.append(junction(xy))
            else:
                ends.append(parcel_stub(xy, pid))
                links_per_parcel[pid] += 1
        edges.append({"u": ends[0], "v": ends[1], "geometry": geom, "objectid": str(oid),
                      "is_parcel_link": any(nodes[n]["kind"] == PARCEL_ACCESS for n in ends)})
    report.parcel_hubs_split = sum(1 for c in links_per_parcel.values() if c >= 2)

    graph = nx.Graph(crs=str(lines.crs), study_area=study_area, buffer_m=buffer_m)
    graph.add_nodes_from(nodes.items())
    for e in edges:
        u, v, geom = e.pop("u"), e.pop("v"), e["geometry"]
        if u == v:
            continue
        if graph.has_edge(u, v):
            # Keep the graph simple: route the parallel line through its own midpoint node.
            report.parallel_edges_split += 1
            mid = geom.interpolate(0.5, normalized=True)
            m = junction((mid.x, mid.y))
            for a, b, part in ((u, m, substring(geom, 0, 0.5, normalized=True)),
                               (m, v, substring(geom, 0.5, 1, normalized=True))):
                graph.add_edge(a, b, **{**e, "geometry": part})
            graph.nodes[m].update(nodes[m])
            continue
        graph.add_edge(u, v, **e)

    comps = sorted(nx.connected_components(graph), key=len, reverse=True)
    for comp in comps[1:]:
        report.components_dropped += 1
        report.nodes_dropped += len(comp)
        graph.remove_nodes_from(comp)
    graph = nx.convert_node_labels_to_integers(graph, ordering="sorted")

    for i, (u, v, data) in enumerate(graph.edges(data=True)):
        data["edge_id"] = f"e{i}"
        data["length_m"] = data["geometry"].length
        data["in_study_area"] = study_area is None or data["geometry"].intersects(study_area)
    for _, data in graph.nodes(data=True):
        data["in_study_area"] = study_area is None or study_area.covers(Point(data["x"], data["y"]))
    report.nodes, report.edges = graph.number_of_nodes(), graph.number_of_edges()
    report.parcels = len({d["parcel_id"] for _, d in graph.nodes(data=True) if d["parcel_id"]})
    return graph, report


def parcel_access_nodes(graph: nx.Graph) -> dict[str, list[int]]:
    """Map parcel_id -> its access stub nodes (one per link into the parcel)."""
    out: dict[str, list[int]] = collections.defaultdict(list)
    for n, d in graph.nodes(data=True):
        if d["kind"] == PARCEL_ACCESS:
            out[d["parcel_id"]].append(n)
    return dict(out)


# ---------------------------------------------------------------------------- persistence

def to_gdfs(graph: nx.Graph) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    crs = graph.graph["crs"]
    nodes = gpd.GeoDataFrame(
        [{"node_id": n, **d, "geometry": Point(d["x"], d["y"])} for n, d in graph.nodes(data=True)],
        geometry="geometry", crs=crs)
    edges = gpd.GeoDataFrame(
        [{"u": u, "v": v, **d} for u, v, d in graph.edges(data=True)], geometry="geometry", crs=crs)
    return nodes, edges


def save_graph(graph: nx.Graph, path: Path) -> None:
    nodes, edges = to_gdfs(graph)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    nodes.to_file(path, layer="nodes", driver="GPKG")
    edges.to_file(path, layer="edges", driver="GPKG")
    if graph.graph.get("study_area") is not None:
        gpd.GeoDataFrame({"buffer_m": [graph.graph["buffer_m"]]}, geometry=[graph.graph["study_area"]],
                         crs=graph.graph["crs"]).to_file(path, layer="study_area", driver="GPKG")


def load_graph(path: Path) -> nx.Graph:
    """Load a graph written by ``save_graph``. All stored node/edge attributes are restored."""
    nodes = gpd.read_file(path, layer="nodes")
    edges = gpd.read_file(path, layer="edges")
    study_area, buffer_m = None, 0.0
    if "study_area" in gpd.list_layers(path).name.values:
        area = gpd.read_file(path, layer="study_area")
        study_area, buffer_m = area.geometry.iloc[0], float(area.buffer_m.iloc[0])
    graph = nx.Graph(crs=str(nodes.crs), study_area=study_area, buffer_m=buffer_m)
    for row in nodes.drop(columns="geometry").to_dict("records"):
        graph.add_node(int(row.pop("node_id")), **{k: _plain(v) for k, v in row.items()})
    for row, geom in zip(edges.drop(columns="geometry").to_dict("records"), edges.geometry):
        u, v = int(row.pop("u")), int(row.pop("v"))
        graph.add_edge(u, v, geometry=geom, **{k: _plain(v) for k, v in row.items()})
    return graph


def _plain(value):
    """Turn pandas/numpy scalars read from file back into plain Python values (NaN -> None)."""
    if value is None or (isinstance(value, float) and value != value):
        return None
    return value.item() if hasattr(value, "item") else value
