"""Snap arbitrary points onto the pedestrian graph and find a route between them.

Each endpoint is connected to *several* nearby footpaths, not just the single nearest one, and
Dijkstra picks whichever gives the cheapest whole route. This matters where paths are stacked:
a point next to a bridge is often nearest to the bridge deck, while the path the person is
actually standing on runs underneath it.

The search itself is delegated to a ``PathFinder`` and the edge cost to a cost function, so
both can be swapped (e.g. a flood-risk cost, or A*) without touching snapping or route assembly.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import networkx as nx
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import substring
from shapely.strtree import STRtree

from floodroute.network.schema import is_snappable
from floodroute.risk.cost import EdgeCost, walking_cost
from floodroute.routing.dijkstra import Dijkstra
from floodroute.routing.pathfinding import NoPathError, PathFinder

WALKING_SPEED_M_S = 1.3  # typical adult walking speed
MAX_SNAP_DISTANCE_M = 100.0  # a point further than this from any footpath is rejected
SNAP_SLACK_M = 15.0  # also consider footpaths up to this much further away than the nearest
MAX_SNAP_CANDIDATES = 6

ORIGIN = "origin"
DESTINATION = "destination"
VIRTUAL = "virtual"
ACCESS_EDGE = "access"


class RoutingError(Exception):
    """A user-facing reason why no route can be produced."""


@dataclass(frozen=True)
class Snap:
    point: Point  # where the user asked for
    snapped: Point  # a point on the network
    distance_m: float
    edge: tuple[int, int]


@dataclass(frozen=True)
class Route:
    nodes: list
    edge_ids: list[str]
    geometry: LineString  # along the network, from origin.snapped to destination.snapped
    length_m: float  # total walk, including the short access legs at both ends
    origin: Snap
    destination: Snap

    @property
    def travel_time_s(self) -> float:
        return self.length_m / WALKING_SPEED_M_S


class Router:
    """Shortest-path routing between arbitrary points inside the study area."""

    def __init__(self, graph: nx.Graph, max_snap_m: float = MAX_SNAP_DISTANCE_M,
                 path_finder: PathFinder | None = None):
        self.graph = graph
        self.study_area: BaseGeometry | None = graph.graph.get("study_area")
        self.max_snap_m = max_snap_m
        self.path_finder = path_finder or Dijkstra()
        self._edges = [(u, v) for u, v, d in graph.edges(data=True) if is_snappable(d)]
        self._geoms = [graph.edges[e]["geometry"] for e in self._edges]
        self._tree = STRtree(self._geoms)

    def snap_candidates(self, point: Point) -> list[Snap]:
        """Footpaths this point could be joined to, nearest first."""
        if self.study_area is not None and not self.study_area.covers(point):
            raise RoutingError("This point is outside Southbank. Please choose a point inside the boundary.")
        nearest = self._geoms[self._tree.nearest(point)].distance(point)
        if nearest > self.max_snap_m:
            raise RoutingError(f"This point is {nearest:.0f} m from the nearest footpath "
                               f"(limit {self.max_snap_m:.0f} m).")
        snaps = []
        for i in self._tree.query(point.buffer(nearest + SNAP_SLACK_M)):
            geom = self._geoms[i]
            distance = geom.distance(point)
            if distance <= nearest + SNAP_SLACK_M:
                snaps.append(Snap(point, geom.interpolate(geom.project(point)), distance, self._edges[i]))
        return sorted(snaps, key=lambda s: s.distance_m)[:MAX_SNAP_CANDIDATES]

    def snap(self, point: Point) -> Snap:
        return self.snap_candidates(point)[0]

    @property
    def footpaths(self) -> list[BaseGeometry]:
        """Geometries of the edges points can snap to."""
        return self._geoms

    def _candidates_for(self, points: Sequence[Point]) -> list[Snap]:
        """Snap candidates for every access point; points that cannot snap are skipped."""
        snaps, first_error = [], None
        for p in points:
            try:
                snaps.extend(self.snap_candidates(p))
            except RoutingError as exc:
                first_error = first_error or exc
        if not snaps:
            raise first_error or RoutingError("No usable point to route from.")
        return snaps

    def route(self, origin: Point | Sequence[Point], destination: Point | Sequence[Point],
              cost: EdgeCost = walking_cost) -> Route:
        """Route between two places, each given as one point or several access points (e.g. a
        building's entrances); the cheapest combination under ``cost`` is used."""
        ends = {ORIGIN: _as_points(origin), DESTINATION: _as_points(destination)}
        candidates = {name: self._candidates_for(points) for name, points in ends.items()}
        graph = self.graph.copy()
        splitter = _EdgeSplitter(graph)
        for name, points in ends.items():
            graph.add_node(name, x=points[0].x, y=points[0].y, kind=VIRTUAL, in_study_area=True)
            for i, snap in enumerate(candidates[name]):
                access = splitter.split(snap, f"{name}_{i}")
                graph.add_edge(name, access, geometry=LineString([snap.point, snap.snapped]),
                               length_m=snap.distance_m, cost_factor=1.0, edge_id=ACCESS_EDGE, snap=snap)
        try:
            nodes = self.path_finder.find_path(graph, ORIGIN, DESTINATION, cost)
        except NoPathError:
            raise RoutingError("No route connects these two points.") from None

        o_snap = graph.edges[nodes[0], nodes[1]]["snap"]
        d_snap = graph.edges[nodes[-2], nodes[-1]]["snap"]
        coords: list = [o_snap.snapped.coords[0]]
        edge_ids, length = [], 0.0
        for a, b in zip(nodes, nodes[1:]):
            data = graph.edges[a, b]
            length += data["length_m"]
            if data["edge_id"] == ACCESS_EDGE:
                continue
            coords.extend(_oriented(data["geometry"], _node_point(graph, a)).coords[1:])
            edge_ids.append(data["edge_id"])
        if len(coords) < 2:  # both ends joined the network at the same spot
            coords.append(d_snap.snapped.coords[0])
        return Route(nodes, edge_ids, LineString(coords), length, o_snap, d_snap)


def _as_points(value: Point | Sequence[Point]) -> list[Point]:
    return [value] if isinstance(value, Point) else list(value)


def _node_point(graph: nx.Graph, n) -> Point:
    return Point(graph.nodes[n]["x"], graph.nodes[n]["y"])


def _oriented(geom: LineString, start: Point) -> LineString:
    """Return ``geom`` running from the end nearest ``start``."""
    if Point(geom.coords[0]).distance(start) <= Point(geom.coords[-1]).distance(start):
        return geom
    return LineString(geom.coords[::-1])


def _piece(geom: LineString, start: float, end: float) -> LineString:
    part = substring(geom, start, end)
    if part.geom_type == "Point":  # zero-length piece at an edge end
        return LineString([part.coords[0], part.coords[0]])
    return part


class _EdgeSplitter:
    """Splits original edges at snapped points, tracking the pieces of edges split more than once."""

    def __init__(self, graph: nx.Graph):
        self.graph = graph
        self.pieces: dict[frozenset, list[tuple]] = {}

    def split(self, snap: Snap, name: str) -> str:
        graph = self.graph
        pieces = self.pieces.setdefault(frozenset(snap.edge), [snap.edge])
        a, b = min(pieces, key=lambda e: graph.edges[e]["geometry"].distance(snap.snapped))
        data = graph.edges[a, b]
        geom = _oriented(data["geometry"], _node_point(graph, a))
        t = geom.project(snap.snapped)
        graph.remove_edge(a, b)
        graph.add_node(name, x=snap.snapped.x, y=snap.snapped.y, kind=VIRTUAL, in_study_area=True)
        for x, y, part, tag in ((a, name, _piece(geom, 0, t), "a"), (name, b, _piece(geom, t, geom.length), "b")):
            graph.add_edge(x, y, **{**data, "geometry": part, "length_m": part.length,
                                    "edge_id": f"{data['edge_id']}{tag}"})
        pieces.remove((a, b))
        pieces.extend([(a, name), (name, b)])
        return name
