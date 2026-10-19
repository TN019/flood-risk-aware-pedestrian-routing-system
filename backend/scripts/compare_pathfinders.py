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

from floodroute import config
from floodroute.benchmark.correctness import TOLERANCE, end_to_end, node_pairs
from floodroute.network import load_graph


def ms(stats: dict) -> str:
    return f"median {stats['median']:.2f} · p95 {stats['p95']:.2f}"


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
        f"- Mismatches: {len(a['mismatches'])}" + (f" — e.g. {a['mismatches'][:5]}" if a["mismatches"] else ""),
        f"- Time per search, in-house (ms): {ms(a['ours_ms'])}",
        f"- Time per search, NetworkX (ms): {ms(a['reference_ms'])}",
        f"- Nodes settled per search (in-house): median {a['settled']['median']:.0f}, "
        f"max {a['settled']['max']} of {graph.number_of_nodes():,}.",
        "",
        "## 2. End to end through the router",
        f"- Routes: {b['routes']:,}; same length: **{b['length_match']:,}** "
        f"({b['length_match'] / b['routes']:.1%}); identical geometry: {b['same_geometry']:,}; "
        f"no route for both: {b['both_none']}.",
        f"- Mismatches: {len(b['mismatches'])}" + (f" — e.g. {b['mismatches'][:3]}" if b["mismatches"] else ""),
    ]
    config.REPORT_DIR.mkdir(exist_ok=True)
    out = config.REPORT_DIR / "pathfinder_comparison.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("report ->", out.relative_to(config.REPO_ROOT))
    if a["mismatches"] or b["mismatches"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
