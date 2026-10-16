"""Edge cost functions used by path finders.

A cost function maps an edge to a non-negative routing cost, or ``None`` when the edge must not
be used (NetworkX convention). Flood-risk costs and safety filtering will be expressed the same
way, combining an edge's attributes with the current hazard snapshot and the traveller's profile.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

EdgeCost = Callable[[Any, Any, dict], "float | None"]


def walking_cost(u, v, data: dict) -> float:
    """Real length, scaled up on edges pedestrians should avoid (``cost_factor`` > 1)."""
    return data["length_m"] * (data.get("cost_factor") or 1.0)
