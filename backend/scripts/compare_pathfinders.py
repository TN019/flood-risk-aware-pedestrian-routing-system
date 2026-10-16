"""Verify the in-house Dijkstra against NetworkX's on the Southbank network.

Two checks, both under the default walking cost (length × cost_factor):

1. Node to node: random node pairs searched directly with each path finder.
2. End to end: random points inside Southbank routed through ``Router`` (snapping, virtual
   nodes, access legs), once with each path finder.

A pair passes when both find a path of the same cost (or both find none). Paths may still differ
when several routes tie on cost, so identical node sequences are reported separately.

Writes reports/pathfinder_comparison.md.

Run:  uv run python scripts/compare_pathfinders.py [--pairs 1000] [--routes 300]
"""

from __future__ import annotations

import argparse
import random
import statistics
import time

from shapely.geometry import Point

from floodroute import config
from floodroute.network import load_graph
from floodroute.risk import walking_cost
from floodroute.routing import Dijkstra, NetworkXDijkstra, NoPathError, Router, RoutingError

TOLERANCE = 1e-6  # metres of cost


def path_cost(graph, path) -> float:
    return sum(walking_cost(u, v, graph.edges[u, v]) for u, v in zip(path, path[1:]))


def timed(fn):
    start = time.perf_counter()
    try:
        out = fn()
    except (NoPathError, RoutingError):
        out = None
    return out, (time.perf_counter() - start) * 1000


def ms_summary(values: list[float]) -> str:
    q = statistics.quantiles(values, n=20)
    return f"mean {statistics.mean(values):.2f} · median {statistics.median(values):.2f} · p95 {q[18]:.2f}"


def node_pairs(graph, n: int, rng: random.Random) -> dict:
    nodes = list(graph.nodes)
    ours, ref = Dijkstra(), NetworkXDijkstra()
    stats = {"pairs": n, "cost_match": 0, "same_path": 0, "both_none": 0, "mismatch": [],
             "ours_ms": [], "ref_ms": [], "settled": []}
    for _ in range(n):
        s, t = rng.sample(nodes, 2)
        result, ours_ms = timed(lambda: ours.search(graph, s, t, walking_cost))
        ref_path, ref_ms = timed(lambda: ref.find_path(graph, s, t, walking_cost))
        stats["ours_ms"].append(ours_ms)
        stats["ref_ms"].append(ref_ms)
        if result is None and ref_path is None:
            stats["both_none"] += 1
            stats["cost_match"] += 1
            continue
        if result is None or ref_path is None:
            stats["mismatch"].append((s, t, "only one found a path"))
            continue
        stats["settled"].append(result.settled)
        if abs(result.cost - path_cost(graph, ref_path)) <= TOLERANCE:
            stats["cost_match"] += 1
            stats["same_path"] += result.path == ref_path
        else:
            stats["mismatch"].append((s, t, f"{result.cost:.3f} vs {path_cost(graph, ref_path):.3f}"))
    return stats


def end_to_end(graph, n: int, rng: random.Random) -> dict:
    ours, ref = Router(graph, path_finder=Dijkstra()), Router(graph, path_finder=NetworkXDijkstra())
    area = graph.graph["study_area"]
    minx, miny, maxx, maxy = area.bounds
    stats = {"routes": 0, "length_match": 0, "same_geometry": 0, "errors_both": 0, "mismatch": []}
    while stats["routes"] < n:
        a, b = (Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy)) for _ in range(2))
        if not (area.contains(a) and area.contains(b)):
            continue
        stats["routes"] += 1
        r1, _ = timed(lambda: ours.route(a, b))
        r2, _ = timed(lambda: ref.route(a, b))
        if r1 is None and r2 is None:
            stats["errors_both"] += 1
            stats["length_match"] += 1
        elif r1 is None or r2 is None:
            stats["mismatch"].append((a.wkt, b.wkt, "only one found a route"))
        elif abs(r1.length_m - r2.length_m) <= TOLERANCE:
            stats["length_match"] += 1
            stats["same_geometry"] += r1.geometry.equals(r2.geometry)
        else:
            stats["mismatch"].append((a.wkt, b.wkt, f"{r1.length_m:.3f} vs {r2.length_m:.3f}"))
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pairs", type=int, default=1000)
    parser.add_argument("--routes", type=int, default=300)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    graph = load_graph(config.PROCESSED_NETWORK_PATH)
    rng = random.Random(args.seed)
    a = node_pairs(graph, args.pairs, rng)
    b = end_to_end(graph, args.routes, rng)

    lines = [
        "# Path finder verification: in-house Dijkstra vs NetworkX",
        "",
        f"Network: {graph.number_of_nodes():,} nodes, {graph.number_of_edges():,} edges. "
        f"Cost: length × cost_factor. Seed {args.seed}. Tolerance {TOLERANCE} m.",
        "",
        "## 1. Node to node",
        f"- Pairs: {a['pairs']:,}; same cost: **{a['cost_match']:,}** "
        f"({a['cost_match'] / a['pairs']:.1%}); identical node sequence: {a['same_path']:,}; "
        f"no path for both: {a['both_none']}.",
        f"- Mismatches: {len(a['mismatch'])}" + (f" — e.g. {a['mismatch'][:5]}" if a["mismatch"] else ""),
        f"- Time per search, in-house (ms): {ms_summary(a['ours_ms'])}",
        f"- Time per search, NetworkX (ms): {ms_summary(a['ref_ms'])}",
        f"- Nodes settled per search (in-house): median {statistics.median(a['settled']):.0f}, "
        f"max {max(a['settled'])} of {graph.number_of_nodes():,}.",
        "",
        "## 2. End to end through the router",
        f"- Routes: {b['routes']:,}; same length: **{b['length_match']:,}** "
        f"({b['length_match'] / b['routes']:.1%}); identical geometry: {b['same_geometry']:,}; "
        f"no route for both: {b['errors_both']}.",
        f"- Mismatches: {len(b['mismatch'])}" + (f" — e.g. {b['mismatch'][:3]}" if b["mismatch"] else ""),
    ]
    config.REPORT_DIR.mkdir(exist_ok=True)
    out = config.REPORT_DIR / "pathfinder_comparison.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("report ->", out.relative_to(config.REPO_ROOT))
    if a["mismatch"] or b["mismatch"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
