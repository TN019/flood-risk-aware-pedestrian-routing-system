"""Run verification cases A–G and compare the results with the predictions in docs/verification.md.

Writes reports/verification_results.md and exits non-zero if any prediction is not met.

Run:  uv run python scripts/verify.py [--trips 100] [--skip-southbank]
"""

from __future__ import annotations

import argparse
import time

from floodroute import config
from floodroute.verification import Check, run_southbank, run_test_town


def fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, tuple):
        return "(" + ", ".join(fmt(v) for v in value) + ")"
    return str(value)


def table(checks: list[Check]) -> list[str]:
    rows = ["| Case | Item | Predicted | Actual | Match |", "|---|---|---|---|---|"]
    for c in checks:
        mark = "info" if c.informational else ("yes" if c.ok else "**NO**")
        rows.append(f"| {c.case} | {c.item} | {fmt(c.predicted)} | {fmt(c.actual)} | {mark} |")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--trips", type=int, default=100)
    parser.add_argument("--skip-southbank", action="store_true")
    args = parser.parse_args()

    start = time.perf_counter()
    town = run_test_town()
    real = [] if args.skip_southbank else run_southbank(args.trips)
    seconds = time.perf_counter() - start

    failed = [c for c in town + real if not c.ok]
    predictions = [c for c in town + real if not c.informational]
    lines = [
        "# Verification: predictions vs results",
        "",
        "Predictions: [docs/verification.md](../docs/verification.md), written before the program was run.",
        f"Result: **{len(predictions) - len(failed)} of {len(predictions)} predictions met** ({seconds:.0f} s).",
        "",
        "## Part 1 — test town (exact values)",
        "",
        *table(town),
    ]
    if real:
        lines += ["", f"## Part 2 — Southbank network ({args.trips} trips per level)", "", *table(real)]
    config.REPORT_DIR.mkdir(exist_ok=True)
    out = config.REPORT_DIR / "verification_results.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("report ->", out.relative_to(config.REPO_ROOT))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
