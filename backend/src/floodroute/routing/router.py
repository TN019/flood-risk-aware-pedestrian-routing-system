"""Snap arbitrary points onto the pedestrian graph and find a route between them.

Each endpoint is connected to *several* nearby footpaths, not just the single nearest one, and
Dijkstra picks whichever gives the cheapest whole route. This matters where paths are stacked:
a point next to a bridge is often nearest to the bridge deck, while the path the person is
actually standing on runs underneath it.

The search itself is delegated to a ``PathFinder`` and the edge cost to a cost function, so
both can be swapped (e.g. a flood-risk cost, or A*) without touching snapping or route assembly.

An access leg (the straight walk from a point to a footpath) that runs alongside or across the
middle of a flight of steps, or passes close to both its ends (a flight that turns back on itself),
is marked ``is_steps`` like the steps themselves; otherwise a leg could join the footpath at the top
of a short flight and so skip the steps for travellers who cannot use them.
"""

from __future__ import annotations

import itertools
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
STANDING_TOLERANCE_M = 1.0  # footpaths this close to the nearest one also count as "standing on"
STEPS_END_M = 1.0  # an access leg may meet a flight of steps within this far of either end (a quarter if shorter)
STEPS_CLEARANCE_M = 0.5  # an access leg this close to the rest of a flight passes it
MAX_SNAP_CANDIDATES = 6

ORIGIN = "origin"
DESTINATION = "destination"
VIRTUAL = "virtual"
ACCESS_EDGE = "access"


class RoutingError(Exception):
    """A user-facing reason why no route can be produced. ``key`` and ``values`` name the reason
    for clients that word it themselves, e.g. in the traveller's language (see ``api.i18n``)."""

    def __init__(self, message: str, key: str | None = None, **values):
        super().__init__(message)
        self.key = key
        self.values = values


@dataclass(frozen=True)
class Snap:
    point: Point  # where the user asked for
    snapped: Point  # a point on the network
    distance_m: float
    edge: tuple[int, int]


@dataclass(frozen=True)
class RouteSegment:
    """One edge of a route as walked: a whole network edge, part of one, or an access leg."""

    source_edge_id: str  # the network edge it lies on (hazard conditions are keyed by this)
    length_m: float
    source_length_m: float  # length of that whole network edge
    is_access: bool = False
    standing_on: tuple[str, ...] = ()  # access legs: footpaths where the traveller starts or ends
    on_steps: bool = False
    gradient: float | None = None  # rise over run of the network edge (None: not measured)


@dataclass(frozen=True)
class Route:
    nodes: list
    edge_ids: list[str]
    geometry: LineString  # along the network, from origin.snapped to destination.snapped
    length_m: float  # total walk, including the short access legs at both ends
    origin: Snap
    destination: Snap
    segments: tuple[RouteSegment, ...] = ()

    @property
    def travel_time_s(self) -> float:
        return self.length_m / WALKING_SPEED_M_S

    @property
    def uses_steps(self) -> bool:
        return any(seg.on_steps for seg in self.segments)

    @property
    def max_gradient(self) -> float | None:
        """The steepest measured gradient on the route (None: none measured)."""
        return max(self._gradients, default=None)

    @property
    def min_gradient(self) -> float | None:
        """The gentlest measured gradient on the route (None: none measured)."""
        return min(self._gradients, default=None)

    @property
    def _gradients(self) -> list[float]:
        return [seg.gradient for seg in self.segments if seg.gradient is not None]


class Router:
    """Shortest-path routing between arbitrary points inside the study area."""

    def __init__(self, graph: nx.Graph, max_snap_m: float = MAX_SNAP_DISTANCE_M, path_finder: PathFinder | None = None):
        self.graph = graph
        self.study_area: BaseGeometry | None = graph.graph.get("study_area")
        self.max_snap_m = max_snap_m
        self.path_finder = path_finder or Dijkstra()
        self._edges = [(u, v) for u, v, d in graph.edges(data=True) if is_snappable(d)]
        self._geoms = [graph.edges[e]["geometry"] for e in self._edges]
        self._tree = STRtree(self._geoms)
        self._steps = [_Flight.of(d["geometry"]) for *_, d in graph.edges(data=True) if d.get("is_steps")]
        self._steps_tree = STRtree([f.line for f in self._steps]) if self._steps else None

    def snap_candidates(self, point: Point) -> list[Snap]:
        """Footpaths this point could be joined to, nearest first."""
        if self.study_area is not None and not self.study_area.covers(point):
            raise RoutingError(
                "This point is outside Southbank. Please choose a point inside the boundary.", "outside_area"
            )
        nearest = self._geoms[self._tree.nearest(point)].distance(point)
        if nearest > self.max_snap_m:
            raise RoutingError(
                f"This point is {nearest:.0f} m from the nearest footpath (limit {self.max_snap_m:.0f} m).",
                "far_from_path",
                distance=f"{nearest:.0f}",
                limit=f"{self.max_snap_m:.0f}",
            )
        snaps = []
        for i in self._tree.query(point.buffer(nearest + SNAP_SLACK_M)):
            geom = self._geoms[i]
            distance = geom.distance(point)
            if distance <= nearest + SNAP_SLACK_M:
                snaps.append(Snap(point, geom.interpolate(geom.project(point)), distance, self._edges[i]))
        return sorted(snaps, key=lambda s: s.distance_m)[:MAX_SNAP_CANDIDATES]

    def snap(self, point: Point) -> Snap:
        return self.snap_candidates(point)[0]

    def passes_steps(self, leg: LineString) -> bool:
        """Whether a straight leg runs past a flight of steps: alongside or across its middle, or close
        to both its ends."""
        if self._steps_tree is None:
            return False
        return any(self._steps[i].passed_by(leg) for i in self._steps_tree.query(leg.buffer(STEPS_END_M)))

    @property
    def footpaths(self) -> list[BaseGeometry]:
        """Geometries of the edges points can snap to."""
        return self._geoms

    def _candidates_for(self, points: Sequence[Point]) -> list[tuple[Snap, tuple[str, ...]]]:
        """Snap candidates for every access point, each with the ids of the footpaths the traveller
        stands on there (all those within ``STANDING_TOLERANCE_M`` of the nearest, e.g. at a
        corner); points that cannot snap are skipped."""
        snaps, first_error = [], None
        for p in points:
            try:
                candidates = self.snap_candidates(p)
            except RoutingError as exc:
                first_error = first_error or exc
                continue
            closest = candidates[0].distance_m + STANDING_TOLERANCE_M
            standing = tuple(self.graph.edges[s.edge]["edge_id"] for s in candidates if s.distance_m <= closest)
            snaps.extend((s, standing) for s in candidates)
        if not snaps:
            raise first_error or RoutingError("No usable point to route from.", "no_usable_point")
        return snaps

    def route(
        self,
        origin: Point | Sequence[Point],
        destination: Point | Sequence[Point],
        cost: EdgeCost = walking_cost,
        path_finder: PathFinder | None = None,
    ) -> Route:
        """Route between two places, each given as one point or several access points (e.g. a
        building's entrances); the cheapest combination under ``cost`` is used. ``path_finder``
        overrides the router's default search for this call."""
        ends = {ORIGIN: _as_points(origin), DESTINATION: _as_points(destination)}
        candidates = {name: self._candidates_for(points) for name, points in ends.items()}
        graph = self.graph.copy()
        splitter = _EdgeSplitter(graph)
        for name, points in ends.items():
            graph.add_node(name, x=points[0].x, y=points[0].y, kind=VIRTUAL, in_study_area=True)
            for i, (snap, standing) in enumerate(candidates[name]):
                access = splitter.split(snap, f"{name}_{i}")
                # The access leg inherits the conditions of the edge it joins and, when that is not
                # one the traveller stands on, of the water where they stand.
                joined = self.graph.edges[snap.edge]
                also = () if joined["edge_id"] in standing else standing
                leg = LineString([snap.point, snap.snapped])
                graph.add_edge(
                    name,
                    access,
                    geometry=leg,
                    length_m=snap.distance_m,
                    cost_factor=1.0,
                    edge_id=ACCESS_EDGE,
                    snap=snap,
                    parent_edge_id=joined["edge_id"],
                    parent_length_m=joined["length_m"],
                    standing_on=also,
                    is_steps=self.passes_steps(leg),
                )
        try:
            nodes = (path_finder or self.path_finder).find_path(graph, ORIGIN, DESTINATION, cost)
        except NoPathError:
            raise RoutingError("No route connects these two points.", "not_connected") from None

        o_snap = graph.edges[nodes[0], nodes[1]]["snap"]
        d_snap = graph.edges[nodes[-2], nodes[-1]]["snap"]
        coords: list = [o_snap.snapped.coords[0]]
        edge_ids, segments, length = [], [], 0.0
        for a, b in itertools.pairwise(nodes):
            data = graph.edges[a, b]
            length += data["length_m"]
            is_access = data["edge_id"] == ACCESS_EDGE
            segments.append(
                RouteSegment(
                    data.get("parent_edge_id") or data["edge_id"],
                    data["length_m"],
                    data.get("parent_length_m") or data["length_m"],
                    is_access,
                    tuple(data.get("standing_on", ())),
                    bool(data.get("is_steps")),
                    data.get("gradient"),
                )
            )
            if is_access:
                continue
            coords.extend(_oriented(data["geometry"], _node_point(graph, a)).coords[1:])
            edge_ids.append(data["edge_id"])
        if len(coords) < 2:  # both ends joined the network at the same spot
            coords.append(d_snap.snapped.coords[0])
        return Route(nodes, edge_ids, LineString(coords), length, o_snap, d_snap, tuple(segments))


def _as_points(value: Point | Sequence[Point]) -> list[Point]:
    return [value] if isinstance(value, Point) else list(value)


def _node_point(graph: nx.Graph, n) -> Point:
    return Point(graph.nodes[n]["x"], graph.nodes[n]["y"])


def _oriented(geom: LineString, start: Point) -> LineString:
    """Return ``geom`` running from the end nearest ``start``."""
    if Point(geom.coords[0]).distance(start) <= Point(geom.coords[-1]).distance(start):
        return geom
    return LineString(geom.coords[::-1])


@dataclass(frozen=True)
class _Flight:
    """A flight of steps as seen by an access leg, which may meet it at its top or bottom but not
    run past the rest of it."""

    line: LineString
    middle: LineString  # the flight without its ends
    ends: tuple[Point, Point]
    end_m: float
    clearance_m: float

    @classmethod
    def of(cls, line: LineString) -> _Flight:
        end = min(STEPS_END_M, line.length / 4)
        middle = _piece(line, end, line.length - end)
        ends = (Point(line.coords[0]), Point(line.coords[-1]))
        return cls(line, middle, ends, end, min(STEPS_CLEARANCE_M, end))

    def passed_by(self, leg: LineString) -> bool:
        if self.middle.distance(leg) < self.clearance_m:
            return True
        return all(p.distance(leg) < self.end_m for p in self.ends)


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
        parent = {
            "parent_edge_id": data.get("parent_edge_id") or data["edge_id"],
            "parent_length_m": data.get("parent_length_m") or data["length_m"],
        }
        for x, y, part, tag in ((a, name, _piece(geom, 0, t), "a"), (name, b, _piece(geom, t, geom.length), "b")):
            graph.add_edge(
                x,
                y,
                **{**data, **parent, "geometry": part, "length_m": part.length, "edge_id": f"{data['edge_id']}{tag}"},
            )
        pieces.remove((a, b))
        pieces.extend([(a, name), (name, b)])
        return name
