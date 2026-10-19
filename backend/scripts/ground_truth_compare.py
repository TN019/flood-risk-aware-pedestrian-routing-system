"""Compare a completed field inspection with the model.

Reads a checklist written by ground_truth_sample.py with its field_ columns filled in, and prints the
agreement and the false accessible rates (items the model treats as usable or step-free that are
not). The same comparison appears on /benchmark once the checklist is filed as
data/ground_truth/inspected.csv and scripts/benchmark.py has run.

Run:  uv run python scripts/ground_truth_compare.py data/ground_truth/inspected.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from floodroute.benchmark import ground_truth


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("checklist", type=Path)
    args = parser.parse_args()
    print(json.dumps(ground_truth.compare(ground_truth.read_csv(args.checklist)), indent=2))


if __name__ == "__main__":
    main()
