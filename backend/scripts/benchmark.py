"""Run every benchmark in docs/benchmarks.md on the Southbank network.

Writes docs/benchmark.json, which the web app shows at /benchmark, and reports/benchmark.md. Takes
about 20 minutes: the fault injection runs the whole test suite once per fault, and the Southbank
verification and safety benchmarks plan a few thousand trips.

Run:  uv run python scripts/benchmark.py [--trips 100] [--skip-faults]
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import time
from datetime import UTC, datetime

from floodroute import config
from floodroute.benchmark import access, correctness, faults, ground_truth, safety
from floodroute.benchmark.world import load_world, random_trips
from floodroute.verification import run_southbank, run_test_town


def rounded(value):
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [rounded(v) for v in value]
    return value


def commit() -> str | None:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True)
        return sha.stdout.strip() + ("+changes" if dirty.stdout.strip() else "")
    except (OSError, subprocess.CalledProcessError):
        return None


def checks(results) -> dict:
    measured = [c for c in results if not c.informational]
    return {
        "met": sum(c.ok for c in measured),
        "total": len(measured),
        "not_met": [f"{c.case}: {c.item}" for c in measured if not c.ok],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--trips", type=int, default=100, help="random trips for the safety benchmarks")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--skip-faults", action="store_true", help="keep the fault injection results already written")
    args = parser.parse_args()

    previous = json.loads(config.BENCHMARK_PATH.read_text()) if config.BENCHMARK_PATH.exists() else {}
    timings = {}

    def timed(name, fn, *a, **k):
        start = time.perf_counter()
        out = fn(*a, **k)
        timings[name] = time.perf_counter() - start
        print(f"{name}: {timings[name]:.0f} s", flush=True)
        return out

    world = timed("loading", load_world)
    rng = random.Random(args.seed)
    out = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": commit(),
        "network": {"nodes": world.graph.number_of_nodes(), "edges": world.graph.number_of_edges()},
        "correctness": {
            "dijkstra_node_pairs": timed("dijkstra node pairs", correctness.node_pairs, world.graph, 1000, rng),
            "dijkstra_end_to_end": timed("dijkstra end to end", correctness.end_to_end, world.graph, 300, rng),
            "minimax_brute_force": timed("minimax", correctness.minimax_against_brute_force, 300, args.seed),
            "verification": {
                "test_town": checks(timed("test town", run_test_town)),
                "southbank": checks(timed("southbank properties", run_southbank, args.trips, args.seed)),
            },
            "faults": previous.get("correctness", {}).get("faults")
            if args.skip_faults
            else timed("fault injection", faults.run_faults),
        },
    }
    trips = random_trips(world, args.trips, args.seed)
    out["safety"] = {
        "cost": timed("safety cost", safety.safety_cost, world, trips),
        "rising_flood": timed(
            "rising flood", safety.rising_flood, world, random_trips(world, args.trips, args.seed + 1, min_m=600)
        ),
    }
    out["access"] = {"step_free_pairs": timed("step-free pairs", access.step_free_pairs, world, 300, args.seed)}
    inspected = config.GROUND_TRUTH_DIR / "inspected.csv"
    out["field"] = ground_truth.compare(ground_truth.read_csv(inspected)) if inspected.exists() else None
    out["seconds"] = timings

    config.BENCHMARK_PATH.write_text(json.dumps(rounded(out), indent=1, ensure_ascii=False) + "\n")
    print("results ->", config.BENCHMARK_PATH.relative_to(config.REPO_ROOT))


if __name__ == "__main__":
    main()
