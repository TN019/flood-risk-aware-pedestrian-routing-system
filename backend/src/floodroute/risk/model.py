"""Edge risk models and the risk-weighted routing cost.

A ``RiskModel`` scores how hazardous an edge is for a given traveller under given conditions:
a non-negative number, or ``None`` when the edge must not be used at all. The routing cost then
adds that risk on top of distance:

    cost = cost_factor × (dry length + wet length × (1 + α·R))

With no water on an edge, R = 0 and the cost is exactly the plain walking cost, so routing with
no flood is identical to routing without the risk layer. α sets how many extra metres of walking
are worth avoiding one metre of water at the traveller's limit (R = 1).

Only the deepest point of an edge is used for R and for the safety check, never an average.
Edges the traveller cannot use at all (steps, for wheelchair users; ``risk.access``) are
impassable whatever the water.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from floodroute.hazard import EdgeCondition, HazardSnapshot
from floodroute.risk.access import can_use
from floodroute.risk.cost import EdgeCost
from floodroute.risk.profile import DRY_DEPTH_M, TravellerProfile

DEFAULT_ALPHA = 2.0


class RiskModel(Protocol):
    def edge_risk(self, condition: EdgeCondition, profile: TravellerProfile) -> float | None:
        """Risk of the wet part of an edge: >= 0, or None if the traveller must not enter it."""
        ...


@dataclass(frozen=True)
class DepthRelativeRisk:
    """Risk from water depth relative to the traveller's own limit.

    - dry (<= 2 cm): 0
    - within the limit: depth / limit, so 1 means "right at your limit"
    - deeper than the limit: impassable
    - unknown depth: impassable by default; set ``unknown_risk`` to route through it at that risk

    Flow velocity is not considered yet.
    """

    unknown_risk: float | None = None

    def edge_risk(self, condition: EdgeCondition, profile: TravellerProfile) -> float | None:
        if condition.depth_m is None:
            return self.unknown_risk
        if condition.depth_m <= DRY_DEPTH_M:
            return 0.0
        limit = profile.depth_limit_m
        if condition.depth_m > limit:
            return None
        return condition.depth_m / limit


def source_edge_id(data: dict) -> str:
    """The network edge an edge (or a piece of one split for routing) came from."""
    return data.get("parent_edge_id") or data["edge_id"]


def _deep(condition: EdgeCondition) -> float:
    return float("inf") if condition.depth_m is None else condition.depth_m


def edge_condition(snapshot: HazardSnapshot, data: dict) -> EdgeCondition:
    """Conditions an edge is walked in.

    An access leg that joins a footpath other than the one the traveller is standing on also
    carries the water where they stand: ``standing_on`` lists the footpaths nearest the point (more
    than one at a corner; they stand on the shallowest). The worse of the two applies to the whole
    leg."""
    condition = snapshot.condition(source_edge_id(data))
    standing_on = data.get("standing_on", ())
    if not standing_on:
        return condition
    standing = min((snapshot.condition(i) for i in standing_on), key=_deep)
    worst = max(condition, standing, key=_deep)
    return EdgeCondition(worst.depth_m, worst.velocity_m_s)


def wet_length(data: dict, condition: EdgeCondition) -> float:
    """Length of this edge (or edge piece) under water, assuming water spreads evenly along it."""
    length = data["length_m"]
    if condition.depth_m is not None and condition.depth_m <= DRY_DEPTH_M:
        return 0.0
    if condition.flooded_length_m is None:
        return length
    parent_length = data.get("parent_length_m") or length
    if parent_length <= 0:
        return 0.0
    return min(length, condition.flooded_length_m * length / parent_length)


def risk_cost(
    snapshot: HazardSnapshot, profile: TravellerProfile, model: RiskModel | None = None, alpha: float = DEFAULT_ALPHA
) -> EdgeCost:
    """Routing cost for ``profile`` under the conditions in ``snapshot``."""
    if alpha < 0:
        raise ValueError("alpha must be >= 0")
    model = model or DepthRelativeRisk()

    def cost(u, v, data: dict) -> float | None:
        if not can_use(profile, data):
            return None
        condition = edge_condition(snapshot, data)
        risk = model.edge_risk(condition, profile)
        if risk is None:
            return None
        wet = wet_length(data, condition)
        factor = data.get("cost_factor") or 1.0
        return factor * (data["length_m"] + wet * alpha * risk)

    return cost
