"""Edges a traveller cannot use at all, whatever the water.

Mobility aid users cannot use steps (``is_steps``, OSM ``highway=steps``) or paths steeper than
``MAX_GRADIENT``, AS 1428.1's steepest ramp (``gradient``, from the City of Melbourne's footpath
steepness data; see ``network.gradient``). Every search made for them applies this rule: the plain
walking cost, the risk cost and the least-water search alike. For everyone else steps and steep
paths are ordinary paths.

An edge without a measured gradient is not treated as steep (see docs/parameters.md).
"""

from __future__ import annotations

from floodroute.network.gradient import STEEPEST_RAMP
from floodroute.risk.cost import EdgeCost, walking_cost
from floodroute.risk.profile import TravellerProfile

MAX_GRADIENT = STEEPEST_RAMP  # the same for manual and powered wheelchairs and mobility scooters


def too_steep(gradient: float | None) -> bool:
    """Whether a path with this gradient (rise over run; None: not measured) is too steep for a
    mobility aid user."""
    return gradient is not None and gradient > MAX_GRADIENT


def can_use(profile: TravellerProfile, data: dict) -> bool:
    """Whether ``profile`` may use this edge regardless of water."""
    return not (profile.uses_wheelchair and (data.get("is_steps") or too_steep(data.get("gradient"))))


def walking_cost_for(profile: TravellerProfile) -> EdgeCost:
    """Plain walking cost, with the edges this traveller cannot use made impassable."""
    if not profile.uses_wheelchair:
        return walking_cost

    def cost(u, v, data: dict) -> float | None:
        return walking_cost(u, v, data) if can_use(profile, data) else None

    return cost
