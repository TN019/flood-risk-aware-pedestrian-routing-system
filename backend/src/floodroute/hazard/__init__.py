"""Hazard layer: flood conditions on network edges from interchangeable providers."""

from floodroute.hazard.base import (
    DRY,
    DRY_DEPTH_M,
    UNKNOWN,
    EdgeCondition,
    HazardProvider,
    HazardSnapshot,
    NoHazard,
)

__all__ = ["DRY", "DRY_DEPTH_M", "UNKNOWN", "EdgeCondition", "HazardProvider", "HazardSnapshot", "NoHazard"]
