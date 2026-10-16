"""Hazard layer: flood conditions on network edges from interchangeable providers."""

from floodroute.hazard.base import DRY, UNKNOWN, EdgeCondition, HazardProvider, HazardSnapshot, NoHazard

__all__ = ["DRY", "UNKNOWN", "EdgeCondition", "HazardProvider", "HazardSnapshot", "NoHazard"]
# Scenario support (floodroute.hazard.scenarios) imports risk.profile, so it is not re-exported here
# to keep hazard importable from risk without a cycle.
