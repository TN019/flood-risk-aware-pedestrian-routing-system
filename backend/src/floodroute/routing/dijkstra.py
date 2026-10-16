"""Dijkstra's shortest-path algorithm with a pluggable edge cost.

Works on any ``networkx.Graph`` and any ``EdgeCost``: the cost may be plain length, length
scaled by ``cost_factor``, or a flood-risk cost. An edge whose cost is ``None`` is impassable.

The search keeps a binary heap of (tentative cost, tie-breaker, node) entries and skips stale
entries when they are popped ("lazy deletion"), which avoids a decrease-key operation. It stops
as soon as the target is settled, since its cost can no longer improve.
"""

from __future__ import annotations

import heapq
import itertools
import time
from dataclasses import dataclass

import networkx as nx

from floodroute.risk.cost import EdgeCost
from floodroute.routing.pathfinding import NoPathError


@dataclass(frozen=True)
class SearchResult:
    path: list
    cost: float
    settled: int  # nodes whose final cost was fixed
    pushed: int  # heap insertions, including stale ones
    seconds: float


class Dijkstra:
    """In-house Dijkstra implementing the ``PathFinder`` protocol."""

    def find_path(self, graph: nx.Graph, source, target, cost: EdgeCost) -> list:
        return self.search(graph, source, target, cost).path

    def search(self, graph: nx.Graph, source, target, cost: EdgeCost) -> SearchResult:
        start = time.perf_counter()
        if source not in graph:
            raise NoPathError(f"source {source!r} is not in the graph")
        if target not in graph:
            raise NoPathError(f"target {target!r} is not in the graph")

        best = {source: 0.0}  # lowest cost found so far
        parent = {source: None}
        settled: set = set()
        tie = itertools.count()  # keeps heap entries comparable when costs are equal
        heap = [(0.0, next(tie), source)]
        pushed = 1

        while heap:
            dist, _, u = heapq.heappop(heap)
            if u in settled or dist > best[u]:
                continue  # stale entry: u was already reached more cheaply
            settled.add(u)
            if u == target:
                return SearchResult(_walk_back(parent, target), dist, len(settled), pushed, time.perf_counter() - start)
            for v, data in graph.adj[u].items():
                if v in settled:
                    continue
                c = cost(u, v, data)
                if c is None:
                    continue  # impassable
                if c < 0:
                    raise ValueError(f"negative edge cost {c} on ({u!r}, {v!r}); Dijkstra needs costs >= 0")
                candidate = dist + c
                if candidate < best.get(v, float("inf")):
                    best[v] = candidate
                    parent[v] = u
                    heapq.heappush(heap, (candidate, next(tie), v))
                    pushed += 1

        raise NoPathError(f"no path from {source!r} to {target!r}")


def _walk_back(parent: dict, target) -> list:
    path = [target]
    while parent[path[-1]] is not None:
        path.append(parent[path[-1]])
    return path[::-1]
