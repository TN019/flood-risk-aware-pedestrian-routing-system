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


def explain(alpha: float, profile: TravellerProfile) -> str:
    """What ``alpha`` means for this traveller, as an example in metres."""
    depth = round(EXAMPLE_DEPTH_SHARE * profile.depth_limit_m, 2)
    if depth <= DRY_DEPTH_M:
        return "You will not walk through water, so routes never enter it; this setting has no effect."
    risk = depth / profile.depth_limit_m
    detour = alpha * risk * EXAMPLE_WATER_M
    return (
        f"To avoid {EXAMPLE_WATER_M:.0f} m of water {depth * 100:.0f} cm deep "
        f"({profile.describe_depth(depth)}), you would walk up to about {_round_m(detour)} m further."
    )


def _round_m(metres: float) -> int:
    step = 5 if metres < 100 else 10
    return int(round(metres / step) * step)
