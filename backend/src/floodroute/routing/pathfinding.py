"""Shortest-path search strategies.

A ``PathFinder`` returns the node sequence of a cheapest path between two nodes under an edge
cost function. Cost functions follow the NetworkX convention: ``cost(u, v, data)`` returns a
non-negative number, or ``None`` to make the edge impassable.

Implementations: ``routing.dijkstra.Dijkstra`` (in-house, the router's default) and
``NetworkXDijkstra`` (reference, used to verify it). Further algorithms (A*, time-dependent
search) implement the same protocol and are passed to ``Router(path_finder=...)``.
"""

from __future__ import annotations

from typing import Protocol

import networkx as nx

from floodroute.risk.cost import EdgeCost


class NoPathError(Exception):
    """No path connects the source to the target under the given cost."""


class PathFinder(Protocol):
    def find_path(self, graph: nx.Graph, source, target, cost: EdgeCost) -> list: ...


class NetworkXDijkstra:
    """Dijkstra's algorithm as implemented by NetworkX; the reference implementation."""

    def find_path(self, graph: nx.Graph, source, target, cost: EdgeCost) -> list:
        try:
            return nx.dijkstra_path(graph, source, target, weight=cost)
        except nx.NetworkXNoPath:
            raise NoPathError(f"no path from {source!r} to {target!r}") from None
