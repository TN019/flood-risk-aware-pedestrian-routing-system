"""Safest-path search: make the deepest water on the way as shallow as possible, then the cost low.

Used when every route crosses water deeper than the traveller would choose, e.g. they are already
standing in it, or to find the least depth limit that would make a trip possible.

The search runs in two phases:

1. Bottleneck search: a Dijkstra variant whose label is the deepest water met so far
   (``max`` instead of ``+``). It finds b*, the lowest possible "deepest point" over all paths.
2. Ordinary cheapest-path search over the edges no deeper than b*.

A single search on the pair (deepest so far, cost so far) would be wrong: two partial paths with
different deepest points can end up equally deep once both cross a deeper edge, and the one that
was discarded may have been the cheaper.
"""

from __future__ import annotations

import heapq
import itertools
import math
from collections.abc import Callable
from typing import Any

import networkx as nx

from floodroute.hazard import HazardSnapshot
from floodroute.risk.access import can_use
from floodroute.risk.cost import EdgeCost
from floodroute.risk.model import edge_condition
from floodroute.risk.profile import TravellerProfile
from floodroute.routing.dijkstra import Dijkstra
from floodroute.routing.pathfinding import NoPathError, PathFinder

EdgeDepth = Callable[[Any, Any, dict], "float | None"]  # deepest water on an edge; None = impassable


def snapshot_depth(snapshot: HazardSnapshot, profile: TravellerProfile | None = None) -> EdgeDepth:
    """Edge depth from a hazard snapshot. Unknown depth counts as infinitely deep: such edges are
    used only when nothing else connects. With a ``profile``, edges that traveller cannot use at all
    (``risk.access``) are impassable, so the deepest point is searched over usable edges only."""

    def depth(u, v, data: dict) -> float | None:
        if profile is not None and not can_use(profile, data):
            return None
        d = edge_condition(snapshot, data).depth_m
        return math.inf if d is None else d

    return depth


def bottleneck_depth(graph: nx.Graph, source, target, depth: EdgeDepth) -> float:
    """The lowest achievable maximum edge depth over all paths from ``source`` to ``target``."""
    best = {source: 0.0}
    done: set = set()
    tie = itertools.count()
    heap = [(0.0, next(tie), source)]
    while heap:
        deepest, _, u = heapq.heappop(heap)
        if u in done:
            continue
        done.add(u)
        if u == target:
            return deepest
        for v, data in graph.adj[u].items():
            if v in done:
                continue
            d = depth(u, v, data)
            if d is None:
                continue
            candidate = max(deepest, d)
            if v not in best or candidate < best[v]:  # not "< inf": unknown-depth edges are inf deep
                best[v] = candidate
                heapq.heappush(heap, (candidate, next(tie), v))
    raise NoPathError(f"no path from {source!r} to {target!r}")


class MinimaxPathFinder:
    """``PathFinder`` returning the cheapest of the paths whose deepest point is as shallow as possible."""

    def __init__(self, depth: EdgeDepth, inner: PathFinder | None = None):
        self.depth = depth
        self.inner = inner or Dijkstra()
        self.last_bottleneck_m: float | None = None

    def find_path(self, graph: nx.Graph, source, target, cost: EdgeCost) -> list:
        limit = bottleneck_depth(graph, source, target, self.depth)
        self.last_bottleneck_m = limit

        def within(u, v, data: dict) -> float | None:
            d = self.depth(u, v, data)
            if d is None or d > limit:
                return None
            return cost(u, v, data)

        return self.inner.find_path(graph, source, target, within)
