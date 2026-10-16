"""How serious the water is where a traveller is standing, judged against their own body.

Levels, from the traveller's height H and their chosen limit:

    OK          at or below their limit
    OVER_LIMIT  deeper than their limit, up to the 30 cm hard limit
    DEEP        deeper than 30 cm                      → emergency help available
    VERY_DEEP   deeper than the knee (0.285·H)         → emergency help recommended
    CRITICAL    deeper than half their height, or unknown → emergency help strongly recommended

Body proportions make the levels stricter for shorter people: a 120 cm child reaches VERY_DEEP
at about 34 cm. Flow velocity is not considered yet, so these levels understate the danger of
moving water.
"""

from __future__ import annotations

from enum import IntEnum

from floodroute.risk.profile import HARD_LIMIT_M, TravellerProfile

KNEE_FRACTION = 0.285
HALF_HEIGHT_FRACTION = 0.5


class AlertLevel(IntEnum):
    OK = 0
    OVER_LIMIT = 1
    DEEP = 2
    VERY_DEEP = 3
    CRITICAL = 4

    @property
    def emergency_advice(self) -> str | None:
        return {
            AlertLevel.DEEP: "available",
            AlertLevel.VERY_DEEP: "recommended",
            AlertLevel.CRITICAL: "strongly recommended",
        }.get(self)


def alert_level(depth_m: float | None, profile: TravellerProfile) -> AlertLevel:
    if depth_m is None:
        return AlertLevel.CRITICAL
    if depth_m > HALF_HEIGHT_FRACTION * profile.height_m:
        return AlertLevel.CRITICAL
    if depth_m > KNEE_FRACTION * profile.height_m:
        return AlertLevel.VERY_DEEP
    if depth_m > HARD_LIMIT_M:
        return AlertLevel.DEEP
    if depth_m > profile.depth_limit_m:
        return AlertLevel.OVER_LIMIT
    return AlertLevel.OK
