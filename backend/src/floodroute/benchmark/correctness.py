"""The path finders against independent references.

- The in-house Dijkstra against NetworkX's, node to node and end to end through the router.
- The two-phase safest-path (minimax) search against enumerating every simple path.

Two results agree when their cost matches within ``TOLERANCE``; paths may still differ when several
tie on cost, so identical paths are counted separately.
"""

from __future__ import annotations

import itertools
import math
import random
import time

import networkx as nx
from shapely.geometry import Point

from floodroute.benchmark.world import quantile
from floodroute.risk import walking_cost
from floodroute.routing import Dijkstra, NetworkXDijkstra, NoPathError, Router, RoutingError
from floodroute.routing.minimax import MinimaxPathFinder

TOLERANCE = 1e-6  # metres of cost

_LENGTH = lambda u, v, d: d["length_m"]  # noqa: E731
_DEPTH = lambda u, v, d: d["depth"]  # noqa: E731


def path_cost(graph: nx.Graph, path: list) -> float:
    return sum(walking_cost(u, v, graph.edges[u, v]) for u, v in itertools.pairwise(path))


def _timed(fn, *args):
    start = time.perf_counter()
    try:
        out = fn(*args)
    except (NoPathError, RoutingError):
        out = None
    return out, (time.perf_counter() - start) * 1000


def _ms(values: list[float]) -> dict:
    return {"median": quantile(values, 0.5), "p95": quantile(values, 0.95)}


def node_pairs(graph: nx.Graph, n: int, rng: random.Random) -> dict:
    """Random node pairs searched with each path finder."""
    nodes = list(graph.nodes)
    ours, ref = Dijkstra(), NetworkXDijkstra()
    out = {"pairs": n, "cost_match": 0, "same_path": 0, "both_none": 0, "mismatches": [], "settled": []}
    ours_ms, ref_ms = [], []
    for _ in range(n):
        s, t = rng.sample(nodes, 2)
        result, a = _timed(ours.search, graph, s, t, walking_cost)
        ref_path, b = _timed(ref.find_path, graph, s, t, walking_cost)
        ours_ms.append(a)
        ref_ms.append(b)
        if result is None and ref_path is None:
            out["both_none"] += 1
            out["cost_match"] += 1
        elif result is None or ref_path is None:
            out["mismatches"].append(f"{s} → {t}: only one found a path")
        elif abs(result.cost - path_cost(graph, ref_path)) <= TOLERANCE:
            out["cost_match"] += 1
            out["same_path"] += result.path == ref_path
            out["settled"].append(result.settled)
        else:
            out["mismatches"].append(f"{s} → {t}: {result.cost:.3f} vs {path_cost(graph, ref_path):.3f}")
    out["ours_ms"], out["reference_ms"] = _ms(ours_ms), _ms(ref_ms)
    out["settled"] = {"median": quantile(out["settled"], 0.5), "max": max(out["settled"], default=None)}
    return out


def end_to_end(graph: nx.Graph, n: int, rng: random.Random) -> dict:
    """Random trips inside the study area routed with each path finder (snapping, access legs)."""
    ours, ref = Router(graph, path_finder=Dijkstra()), Router(graph, path_finder=NetworkXDijkstra())
    area = graph.graph["study_area"]
    minx, miny, maxx, maxy = area.bounds
    out = {"routes": 0, "length_match": 0, "same_geometry": 0, "both_none": 0, "mismatches": []}
    times = []
    while out["routes"] < n:
        a, b = (Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy)) for _ in range(2))
        if not (area.contains(a) and area.contains(b)):
            continue
        out["routes"] += 1
        r1, ms = _timed(ours.route, a, b)
        r2, _ = _timed(ref.route, a, b)
        times.append(ms)
        if r1 is None and r2 is None:
            out["both_none"] += 1
            out["length_match"] += 1
        elif r1 is None or r2 is None:
            out["mismatches"].append(f"{a.wkt} → {b.wkt}: only one found a route")
        elif abs(r1.length_m - r2.length_m) <= TOLERANCE:
            out["length_match"] += 1
            out["same_geometry"] += r1.geometry.equals(r2.geometry)
        else:
            out["mismatches"].append(f"{a.wkt} → {b.wkt}: {r1.length_m:.3f} vs {r2.length_m:.3f}")
    out["route_ms"] = _ms(times)
    return out


def minimax_against_brute_force(graphs: int = 300, seed: int = 2026) -> dict:
    """Random small graphs: the safest path must have the lowest possible deepest point, and among
    paths that deep the shortest length, exactly as enumerating every simple path finds."""
    out = {"graphs": graphs, "pairs": 0, "match": 0, "mismatches": []}
    for i in range(graphs):
        rng = random.Random(seed + i)
        g = nx.gnm_random_graph(9, 16, seed=seed + i)
        for u, v in g.edges:
            g.edges[u, v]["length_m"] = rng.uniform(1, 100)
            g.edges[u, v]["depth"] = rng.choice([0.0, 0.0, 0.05, 0.1, 0.2, 0.35, 0.6])
        for s, t in [(0, 8), (1, 7), (2, 5)]:
            if not nx.has_path(g, s, t):
                continue
            out["pairs"] += 1
            best = min(
                (
                    max(g.edges[a, b]["depth"] for a, b in itertools.pairwise(p)),
                    sum(g.edges[a, b]["length_m"] for a, b in itertools.pairwise(p)),
                )
                for p in nx.all_simple_paths(g, s, t)
            )
            path = MinimaxPathFinder(_DEPTH).find_path(g, s, t, _LENGTH)
            got = (
                max(g.edges[a, b]["depth"] for a, b in itertools.pairwise(path)),
                sum(g.edges[a, b]["length_m"] for a, b in itertools.pairwise(path)),
            )
            if math.isclose(got[0], best[0], abs_tol=1e-9) and math.isclose(got[1], best[1], abs_tol=1e-6):
                out["match"] += 1
            else:
                out["mismatches"].append(f"graph {i}, {s} → {t}: {got} vs {best}")
    return out
