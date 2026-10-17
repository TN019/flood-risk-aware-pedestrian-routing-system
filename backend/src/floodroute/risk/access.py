"""Edges a traveller cannot use at all, whatever the water.

Wheelchair users cannot use steps (``is_steps``, OSM ``highway=steps``). Every search made for them
applies this rule: the plain walking cost, the risk cost and the least-water search alike. For
everyone else steps are ordinary paths.

Steep paths are not filtered: OSM's ``incline`` tag in Southbank only says ``up``, ``down`` or
``yes``, never a gradient that could be compared with a ramp limit (see docs/parameters.md).
"""

from __future__ import annotations

from floodroute.risk.cost import EdgeCost, walking_cost
from floodroute.risk.profile import TravellerProfile


def can_use(profile: TravellerProfile, data: dict) -> bool:
    """Whether ``profile`` may use this edge regardless of water."""
    return not (profile.uses_wheelchair and data.get("is_steps"))


def walking_cost_for(profile: TravellerProfile) -> EdgeCost:
    """Plain walking cost, with the edges this traveller cannot use made impassable."""
    if not profile.uses_wheelchair:
        return walking_cost

    def cost(u, v, data: dict) -> float | None:
        return walking_cost(u, v, data) if can_use(profile, data) else None

    return cost
