"""Risk assessment and routing costs: how hazard conditions and a traveller's limits turn into
edge costs and impassable edges."""

from floodroute.risk.access import MAX_GRADIENT, can_use, too_steep, walking_cost_for
from floodroute.risk.cost import EdgeCost, walking_cost
from floodroute.risk.model import DEFAULT_ALPHA, DepthRelativeRisk, RiskModel, risk_cost
from floodroute.risk.profile import (
    DRY_DEPTH_M,
    HARD_LIMIT_M,
    AidLevel,
    BodyPart,
    MobilityAid,
    TravellerProfile,
    describe_depth,
)

__all__ = [
    "DEFAULT_ALPHA",
    "DRY_DEPTH_M",
    "HARD_LIMIT_M",
    "MAX_GRADIENT",
    "AidLevel",
    "BodyPart",
    "DepthRelativeRisk",
    "EdgeCost",
    "MobilityAid",
    "RiskModel",
    "TravellerProfile",
    "can_use",
    "describe_depth",
    "risk_cost",
    "too_steep",
    "walking_cost",
    "walking_cost_for",
]
