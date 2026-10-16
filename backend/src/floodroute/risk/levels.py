"""Flood levels defined by how deep the water is on an adult's body.

A flood scenario's level comes from its typical depth: the median depth, weighted by length, of
the water on flooded footpaths inside the study area. The bands follow body landmarks of a
reference adult:

| Level    | Typical depth           | Reference adult (1.70 m) |
|----------|-------------------------|--------------------------|
| Light    | up to the ankle         | up to 6.6 cm             |
| Moderate | over the calf, to knee  | 6.6 to 48.5 cm           |
| Heavy    | over the thigh, to hip  | 48.5 to 90.1 cm          |
| Extreme  | above the hip           | over 90.1 cm             |

Ankle, knee and hip are the waterlines used to grade flood severity from photographs of people
(Feng, Brenner & Sester 2020), placed at Drillis & Contini's proportions of stature (0.039, 0.285
and 0.530). Knee height is also where hazard guidance draws its first limits for people: 0.5 m
is the H2 depth limit and the most children can safely wade (Smith, Davey & Cox 2014), and
Melbourne Water's limit for safe pedestrian access in Southbank.
"""

from __future__ import annotations

from enum import Enum

import networkx as nx
import numpy as np

from floodroute.hazard.base import DRY_DEPTH_M, HazardSnapshot
from floodroute.risk.alerts import KNEE_FRACTION
from floodroute.risk.profile import BodyPart

REFERENCE_HEIGHT_M = 1.70  # Australian adults average 1.69 m (ABS Australian Health Survey 2011-12)
ANKLE_FRACTION = BodyPart.ANKLE.value
HIP_FRACTION = 0.530


class FloodLevel(Enum):
    """Upper bound of each level as a fraction of the reference adult's height (None = no bound)."""

    LIGHT = ANKLE_FRACTION
    MODERATE = KNEE_FRACTION
    HEAVY = HIP_FRACTION
    EXTREME = None

    @property
    def label(self) -> str:
        return self.name.capitalize()

    @property
    def body_range(self) -> str:
        return {
            "LIGHT": "up to an adult's ankle",
            "MODERATE": "over the calf, up to the knee",
            "HEAVY": "over the thigh, up to the hip",
            "EXTREME": "above the hip",
        }[self.name]

    @property
    def upper_m(self) -> float | None:
        return None if self.value is None else self.value * REFERENCE_HEIGHT_M

    @property
    def lower_m(self) -> float:
        levels = list(FloodLevel)
        i = levels.index(self)
        return DRY_DEPTH_M if i == 0 else levels[i - 1].upper_m


def level_of(depth_m: float) -> FloodLevel:
    for level in FloodLevel:
        if level.upper_m is None or depth_m <= level.upper_m:
            return level
    raise AssertionError("unreachable")


def typical_depth_m(snapshot: HazardSnapshot, graph: nx.Graph) -> float | None:
    """Length-weighted median depth on the flooded edges inside the study area; None when dry.
    Edges of unknown depth are left out."""
    depths, lengths = [], []
    for *_, d in graph.edges(data=True):
        if not d.get("in_study_area"):
            continue
        c = snapshot.conditions.get(d["edge_id"])
        if c is None or c.depth_m is None or c.depth_m <= DRY_DEPTH_M:
            continue
        depths.append(c.depth_m)
        lengths.append(min(c.flooded_length_m or d["length_m"], d["length_m"]))
    if not depths:
        return None
    order = np.argsort(depths)
    share = np.cumsum(np.asarray(lengths)[order]) / sum(lengths)
    return float(np.asarray(depths)[order][np.searchsorted(share, 0.5)])
