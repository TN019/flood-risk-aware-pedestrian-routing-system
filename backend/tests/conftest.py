"""With FLOODROUTE_FAULT set (e.g. F1), the whole run breaks that safety rule on purpose; see
floodroute.benchmark.faults. Unset, as in every normal run, nothing changes."""

import contextlib
import os

_fault = contextlib.ExitStack()


def pytest_configure(config):
    key = os.environ.get("FLOODROUTE_FAULT")
    if key:
        from floodroute.benchmark.faults import applied

        _fault.enter_context(applied(key))


def pytest_unconfigure(config):
    _fault.close()
