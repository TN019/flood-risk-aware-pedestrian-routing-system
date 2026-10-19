"""Draw a stratified sample of footpath sections and building entrances to inspect on site.

Writes a checklist (CSV) with what the model says about each item and empty field_ columns for the
inspector; see docs/benchmarks.md (3.2) and floodroute.benchmark.ground_truth for the answers
expected. File the completed checklist as data/ground_truth/inspected.csv.

Run:  uv run python scripts/ground_truth_sample.py [--per-kind 15] [--out data/ground_truth/sample.csv]
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from floodroute import config
from floodroute.benchmark import ground_truth
from floodroute.benchmark.world import load_world


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--per-kind", type=int, default=15, help="items of each kind of path, and entrances")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out", type=Path, default=config.GROUND_TRUTH_DIR / "sample.csv")
    args = parser.parse_args()

    rows = ground_truth.sample(load_world(), args.per_kind, args.seed)
    ground_truth.write_csv(rows, args.out)
    for kind, n in Counter(r["category"] for r in rows).items():
        print(f"{kind}: {n}")
    print(f"{len(rows)} items -> {args.out}")


if __name__ == "__main__":
    main()
