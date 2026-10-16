"""A traveller's wading limit, expressed as a body part and converted to a depth via height.

People choose the deepest water they accept as a part of their body ("up to my ankle"), which is
easier to judge than centimetres. The part is converted to a depth with standard anthropometric
proportions of standing height (Drillis & Contini), and never exceeds ``HARD_LIMIT_M`` whatever
the height or choice. Wheelchair users are limited to water no deeper than ``DRY_DEPTH_M``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from floodroute.hazard.base import DRY_DEPTH_M

# Nobody is routed through deeper water. Melbourne Water's Southbank floodplain plan takes up to
# 500 mm as safe pedestrian access; 0.5 m is also the H2 depth limit for people.
HARD_LIMIT_M = 0.50
DEFAULT_WALKING_SPEED_M_S = 1.3


class BodyPart(Enum):
    """Deepest acceptable water, as a fraction of standing height (None = no wading at all)."""

    NO_WADING = None
    ANKLE = 0.039
    LOWER_CALF = 0.121
    MID_CALF = 0.162
    KNEE = 0.285

    @property
    def label(self) -> str:
        return {
            "NO_WADING": "no wading",
            "ANKLE": "ankle",
            "LOWER_CALF": "lower calf",
            "MID_CALF": "mid calf",
            "KNEE": "knee",
        }[self.name]


# Body landmarks used to describe a depth, as fractions of standing height.
LANDMARKS = (
    (0.039, "ankle"),
    (0.121, "lower calf"),
    (0.162, "mid calf"),
    (0.285, "knee"),
    (0.41, "mid thigh"),
    (0.53, "hip"),
    (0.63, "waist"),
    (0.72, "chest"),
    (0.818, "shoulders"),
)


@dataclass(frozen=True)
class TravellerProfile:
    height_m: float
    max_wading: BodyPart = BodyPart.NO_WADING
    uses_wheelchair: bool = False
    walking_speed_m_s: float = DEFAULT_WALKING_SPEED_M_S

    def __post_init__(self):
        if not 0.5 <= self.height_m <= 2.5:
            raise ValueError(f"height {self.height_m} m is outside 0.5–2.5 m")
        if self.walking_speed_m_s <= 0:
            raise ValueError("walking speed must be positive")

    @property
    def depth_limit_m(self) -> float:
        """Deepest water this traveller may be routed through."""
        if self.uses_wheelchair or self.max_wading is BodyPart.NO_WADING:
            return DRY_DEPTH_M
        return max(DRY_DEPTH_M, min(self.max_wading.value * self.height_m, HARD_LIMIT_M))

    def describe_depth(self, depth_m: float | None) -> str:
        return describe_depth(depth_m, self.height_m)


def describe_depth(depth_m: float | None, height_m: float) -> str:
    """Where water of this depth reaches on a person of this height, e.g. "up to the ankle"."""
    if depth_m is None:
        return "unknown depth"
    if depth_m <= DRY_DEPTH_M:
        return "dry"
    for fraction, name in LANDMARKS:
        if depth_m <= fraction * height_m:
            return f"up to the {name}"
    return "above the shoulders"
