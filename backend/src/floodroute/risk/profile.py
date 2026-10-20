"""A traveller's wading limit, expressed as a body part and converted to a depth via height.

People choose the deepest water they accept as a part of their body ("up to my ankle"), which is
easier to judge than centimetres. The part is converted to a depth with standard anthropometric
proportions of standing height (Drillis & Contini), and never exceeds ``HARD_LIMIT_M`` whatever
the height or choice.

Travellers with a wheeled mobility aid pick a level of their device instead (``MobilityAid``):
standing-height proportions do not apply, and what limits them is the device. No study measures
the stability of an occupied wheelchair or scooter in floodwater, so the levels follow device
geometry and manufacturer instructions (see docs/parameters.md, which marks the judgement values).
Every level starts at no water, and each device has its own cap, far below the 50 cm for walkers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from floodroute.hazard.base import DRY_DEPTH_M

# Nobody is routed through deeper water. Melbourne Water's Southbank floodplain plan takes up to
# 500 mm as safe pedestrian access; 0.5 m is also the H2 depth limit for people.
HARD_LIMIT_M = 0.50
DEFAULT_WALKING_SPEED_M_S = 1.3


@dataclass(frozen=True)
class AidLevel:
    key: str
    label: str  # what the water reaches, e.g. "below a 4-inch castor axle"
    depth_m: float


DRY_LEVEL = AidLevel("no_water", "no water", DRY_DEPTH_M)


class MobilityAid(Enum):
    """A wheeled mobility aid and the water levels it may be routed through, lowest first; the last
    level is the device's cap."""

    NONE = ()
    MANUAL_WHEELCHAIR = (
        DRY_LEVEL,
        # A 4-inch front castor's axle is 5.1 cm high; manufacturers also limit kerbs to 5 cm.
        AidLevel("below_castor_axle", "below a 4-inch castor axle", 0.05),
        # A 6-inch castor's axle is 7.6 cm high (judgement: no source sets a wading depth).
        AidLevel("below_large_castor_axle", "below a 6-inch castor axle", 0.075),
    )
    POWERED_WHEELCHAIR = (
        DRY_LEVEL,
        # About 7.5 cm of ground clearance, electrics rated only for spray (IPX4); the 2.5 cm margin
        # is a judgement.
        AidLevel("below_chassis", "well below the chassis", 0.05),
    )
    MOBILITY_SCOOTER = (
        DRY_LEVEL,
        # Manufacturer instruction: do not cross water deeper than 2.5 cm; motor clearance 3.5 cm.
        AidLevel("shallow_puddle", "a shallow puddle", 0.025),
    )

    @property
    def levels(self) -> tuple[AidLevel, ...]:
        return self.value

    @property
    def label(self) -> str:
        return {
            "NONE": "none",
            "MANUAL_WHEELCHAIR": "manual wheelchair",
            "POWERED_WHEELCHAIR": "powered wheelchair",
            "MOBILITY_SCOOTER": "mobility scooter",
        }[self.name]

    @property
    def cap_m(self) -> float:
        return self.value[-1].depth_m if self.value else HARD_LIMIT_M


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
    """``uses_wheelchair=True`` on its own means a manual wheelchair at its lowest level (no water);
    with ``mobility_aid`` set, ``uses_wheelchair`` is true for any wheeled aid and ``aid_level``
    picks the level. ``max_wading`` applies only without an aid."""

    height_m: float
    max_wading: BodyPart = BodyPart.NO_WADING
    uses_wheelchair: bool = False
    walking_speed_m_s: float = DEFAULT_WALKING_SPEED_M_S
    mobility_aid: MobilityAid = MobilityAid.NONE
    aid_level: int = 0

    def __post_init__(self):
        if not 0.5 <= self.height_m <= 2.5:
            raise ValueError(f"height {self.height_m} m is outside 0.5–2.5 m")
        if self.walking_speed_m_s <= 0:
            raise ValueError("walking speed must be positive")
        if self.uses_wheelchair and self.mobility_aid is MobilityAid.NONE:
            object.__setattr__(self, "mobility_aid", MobilityAid.MANUAL_WHEELCHAIR)
        if self.mobility_aid is not MobilityAid.NONE:
            object.__setattr__(self, "uses_wheelchair", True)
            if not 0 <= self.aid_level < len(self.mobility_aid.levels):
                raise ValueError(f"a {self.mobility_aid.label} has no level {self.aid_level}")

    @property
    def aid(self) -> AidLevel | None:
        return self.mobility_aid.levels[self.aid_level] if self.uses_wheelchair else None

    @property
    def depth_limit_m(self) -> float:
        """Deepest water this traveller may be routed through."""
        if self.aid is not None:
            return self.aid.depth_m
        if self.max_wading is BodyPart.NO_WADING:
            return DRY_DEPTH_M
        return max(DRY_DEPTH_M, min(self.max_wading.value * self.height_m, HARD_LIMIT_M))

    @property
    def hard_limit_m(self) -> float:
        """The most this traveller could ever be routed through: 50 cm, or their device's cap."""
        return self.mobility_aid.cap_m

    def describe_depth(self, depth_m: float | None) -> str:
        return describe_depth(depth_m, self.height_m)


# What ``depth_reach`` returns besides a landmark's name.
UNKNOWN_DEPTH, DRY, ABOVE_SHOULDERS = "unknown depth", "dry", "above the shoulders"


def depth_reach(depth_m: float | None, height_m: float) -> str:
    """Where water of this depth reaches on a person of this height: the first landmark of
    ``LANDMARKS`` it does not pass (e.g. "ankle"), or ``UNKNOWN_DEPTH``, ``DRY`` or
    ``ABOVE_SHOULDERS``. The web API words it in the traveller's language."""
    if depth_m is None:
        return UNKNOWN_DEPTH
    if depth_m <= DRY_DEPTH_M:
        return DRY
    for fraction, name in LANDMARKS:
        if depth_m <= fraction * height_m:
            return name
    return ABOVE_SHOULDERS


def describe_depth(depth_m: float | None, height_m: float) -> str:
    """Where water of this depth reaches on a person of this height, e.g. "up to the ankle"."""
    reach = depth_reach(depth_m, height_m)
    return reach if reach in (UNKNOWN_DEPTH, DRY, ABOVE_SHOULDERS) else f"up to the {reach}"
