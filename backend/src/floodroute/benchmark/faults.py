"""Safety rules broken on purpose, to show that the tests notice (fault injection).

Each fault patches one rule. ``run_faults`` runs the whole test suite once per fault, in a separate
process with ``FLOODROUTE_FAULT`` set (tests/conftest.py applies it), and also the test town cases in
this process, so each fault is reported with the tests and the verification cases it breaks. A fault
no test notices is a gap in the tests.
"""

from __future__ import annotations

import contextlib
import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from floodroute import config
from floodroute.hazard.base import DRY_DEPTH_M

ENV = "FLOODROUTE_FAULT"
TESTS_DIR = config.REPO_ROOT / "backend" / "tests"


@dataclass(frozen=True)
class Fault:
    key: str
    breaks: str
    patches: Callable[[], list]  # the mock patchers that break the rule


def _over_limit_passable() -> list:
    from floodroute.risk.model import DepthRelativeRisk

    def edge_risk(self, condition, profile):
        if condition.depth_m is None:
            return self.unknown_risk
        if condition.depth_m <= DRY_DEPTH_M:
            return 0.0
        return condition.depth_m / profile.depth_limit_m  # no "deeper than the limit: impassable"

    return [mock.patch.object(DepthRelativeRisk, "edge_risk", edge_risk)]


def _unknown_is_dry() -> list:
    from floodroute.risk.model import DepthRelativeRisk

    original = DepthRelativeRisk.edge_risk

    def edge_risk(self, condition, profile):
        return 0.0 if condition.depth_m is None else original(self, condition, profile)

    return [mock.patch.object(DepthRelativeRisk, "edge_risk", edge_risk)]


def _no_hard_limit() -> list:
    return [mock.patch("floodroute.risk.profile.HARD_LIMIT_M", 10.0)]


def _steps_for_wheelchairs() -> list:
    anyone = lambda profile, data: True  # noqa: E731
    return [
        mock.patch(f"{module}.can_use", anyone)
        for module in ("floodroute.risk.access", "floodroute.risk.model", "floodroute.routing.minimax")
    ]


def _steep_for_wheelchairs() -> list:
    return [mock.patch("floodroute.risk.access.MAX_GRADIENT", float("inf"))]


def _no_refuge() -> list:
    return [mock.patch("floodroute.trip.find_refuge", lambda *a, **k: None)]


def _no_downgrade() -> list:
    return [mock.patch("floodroute.trip.find_downgrade", lambda *a, **k: None)]


def _no_help_when_cut_off() -> list:
    from floodroute import trip

    original = trip.emergency_advice

    def advice(*args, **kwargs):
        offered, reason = original(*args, **kwargs)
        return (None, trip.FROM_DEPTH) if reason == trip.CUT_OFF else (offered, reason)

    return [mock.patch("floodroute.trip.emergency_advice", advice)]


def _no_help() -> list:
    from floodroute import trip

    return [mock.patch("floodroute.trip.emergency_advice", lambda *a, **k: (None, trip.FROM_DEPTH))]


def _alpha_zero() -> list:
    from floodroute.routing import planning

    original = planning.plan_routes

    def plan_routes(router, origin, destination, snapshot, profile, alpha=0.0, *args, **kwargs):
        return original(router, origin, destination, snapshot, profile, 0.0, *args, **kwargs)

    return [
        mock.patch(f"{module}.plan_routes", plan_routes)
        for module in ("floodroute.routing.planning", "floodroute.routing", "floodroute.trip")
    ]


FAULTS: dict[str, Fault] = {
    f.key: f
    for f in [
        Fault("F1", "Water deeper than the limit is passable", _over_limit_passable),
        Fault("F2", "Water of unknown depth counts as dry", _unknown_is_dry),
        Fault("F3", "No 50 cm hard limit for walkers", _no_hard_limit),
        Fault("F4", "Wheelchair users may use steps", _steps_for_wheelchairs),
        Fault("F5", "No refuge is offered", _no_refuge),
        Fault("F6", "No downgrade is offered", _no_downgrade),
        Fault("F7", "No emergency help when cut off inside a building", _no_help_when_cut_off),
        Fault("F8", "No emergency help at all", _no_help),
        Fault("F9", "The recommended route ignores water within the limit (α = 0)", _alpha_zero),
        Fault("F10", "Mobility aid users may use paths steeper than 1:14", _steep_for_wheelchairs),
    ]
}


@contextlib.contextmanager
def applied(key: str) -> Iterator[Fault]:
    """Break the rule while inside the block."""
    fault = FAULTS[key]
    with contextlib.ExitStack() as stack:
        for patcher in fault.patches():
            stack.enter_context(patcher)
        yield fault


_FAILED = re.compile(r"^FAILED (\S+)")
_SUMMARY = re.compile(r"(\d+) (failed|passed|skipped|error|errors)")


def run_suite(fault: str | None, tests_dir: Path = TESTS_DIR) -> dict:
    """The whole test suite in a separate process, with ``fault`` applied (None: as written)."""
    env = {k: v for k, v in os.environ.items() if k != ENV}
    if fault:
        env[ENV] = fault
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--tb=no", "-rf", str(tests_dir)],
        cwd=tests_dir.parent,
        env=env,
        capture_output=True,
        text=True,
    )
    counts = {"failed": 0, "passed": 0, "skipped": 0}
    for n, kind in _SUMMARY.findall(proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""):
        counts["failed" if kind.startswith("error") else kind] += int(n)
    failed = [m.group(1) for line in proc.stdout.splitlines() if (m := _FAILED.match(line))]
    return {**counts, "failed_tests": failed}


def run_faults(keys: list[str] | None = None) -> dict:
    """Every fault against the test suite and the test town; the suite as written first."""
    from floodroute.verification import run_test_town

    baseline = run_suite(None)
    results = []
    for key in keys or list(FAULTS):
        suite = run_suite(key)
        with applied(key):
            town = sorted({c.case for c in run_test_town() if not c.ok})
        results.append(
            {
                "fault": key,
                "breaks": FAULTS[key].breaks,
                "tests_failed": suite["failed"],
                "tests_run": suite["failed"] + suite["passed"],
                "failed_tests": suite["failed_tests"],
                "test_town_cases_failed": town,
                "caught": suite["failed"] > 0,
            }
        )
    return {"baseline": {k: baseline[k] for k in ("failed", "passed", "skipped")}, "faults": results}
