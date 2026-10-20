"""Route preferences: plain-language settings for the risk weight α.

α is how many extra metres a traveller would walk to avoid one metre of water that is right at
their limit; for shallower water the trade-off scales down in proportion (see ``risk.model``).
Water over the limit is never used whatever the preference, so a preference only decides
whether water *within* the limit is worth walking around.

``explain`` turns a preference into a concrete example for a given traveller, so they can see
what it means for them, e.g. "To avoid 50 m of water 5 cm deep (up to the ankle), you would walk
up to about 75 m further."
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from floodroute.hazard import DRY_DEPTH_M
from floodroute.risk.profile import TravellerProfile

EXAMPLE_WATER_M = 50.0  # length of water in the example sentence
EXAMPLE_DEPTH_SHARE = 0.75  # example water depth, as a share of the traveller's limit


class RoutePreference(Enum):
    SHORTEST = 0.5
    BALANCED = 2.0
    AVOID_WATER = 5.0
    DRIEST = 15.0

    @property
    def alpha(self) -> float:
        return self.value

    @property
    def label(self) -> str:
        return {
            "SHORTEST": "Shortest",
            "BALANCED": "Balanced",
            "AVOID_WATER": "Avoid water",
            "DRIEST": "Stay as dry as possible",
        }[self.name]

    @property
    def summary(self) -> str:
        return {
            "SHORTEST": "Take the shorter way through water within your limit.",
            "BALANCED": "Walk a bit further to stay out of water close to your limit.",
            "AVOID_WATER": "Walk noticeably further to avoid water within your limit.",
            "DRIEST": "Walk much further, if needed, to keep out of water.",
        }[self.name]


DEFAULT_PREFERENCE = RoutePreference.BALANCED


@dataclass(frozen=True)
class Example:
    """To avoid ``water_m`` of water ``depth_m`` deep, a traveller would walk up to ``detour_m`` further."""

    water_m: float
    depth_m: float
    detour_m: int


def example(alpha: float, profile: TravellerProfile) -> Example | None:
    """What ``alpha`` means for this traveller, in metres; None when they do not walk through water
    at all, so the setting has no effect."""
    depth = round(EXAMPLE_DEPTH_SHARE * profile.depth_limit_m, 2)
    if depth <= DRY_DEPTH_M:
        return None
    risk = depth / profile.depth_limit_m
    return Example(EXAMPLE_WATER_M, depth, _round_m(alpha * risk * EXAMPLE_WATER_M))


def explain(alpha: float, profile: TravellerProfile) -> str:
    """What ``alpha`` means for this traveller, as an example in metres."""
    ex = example(alpha, profile)
    if ex is None:
        return "You will not walk through water, so routes never enter it; this setting has no effect."
    return (
        f"To avoid {ex.water_m:.0f} m of water {ex.depth_m * 100:.0f} cm deep "
        f"({profile.describe_depth(ex.depth_m)}), you would walk up to about {ex.detour_m} m further."
    )


def _round_m(metres: float) -> int:
    step = 5 if metres < 100 else 10
    return int(round(metres / step) * step)
