"""Verification cases A–F (docs/verification.md): every hand-derived prediction must hold."""

import pytest

from floodroute import config
from floodroute.verification import run_southbank, run_test_town


def test_test_town_matches_every_hand_derived_prediction():
    failed = [c for c in run_test_town() if not c.ok]
    assert not failed, failed


@pytest.mark.skipif(
    not (config.PROCESSED_NETWORK_PATH.exists() and config.PROCESSED_PLACES_PATH.exists()),
    reason="processed network not built",
)
def test_southbank_properties_hold():
    failed = [c for c in run_southbank(trips=10) if not c.ok]
    assert not failed, failed
