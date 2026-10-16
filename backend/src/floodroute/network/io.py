"""Save and load routing graphs as GeoPackage (layers: nodes, edges, study_area)."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import networkx as nx
from shapely.geometry import Point


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
