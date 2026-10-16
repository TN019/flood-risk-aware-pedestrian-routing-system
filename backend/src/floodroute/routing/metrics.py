"""Measures of a route's flood exposure, reported alongside (not folded into) its routing cost."""

from __future__ import annotations

from dataclasses import dataclass

from floodroute.hazard import DRY_DEPTH_M, HazardSnapshot
from floodroute.risk.model import wet_length
from floodroute.risk.profile import TravellerProfile
from floodroute.routing.router import Route


@dataclass(frozen=True)
class RouteMetrics:
    length_m: float
    travel_time_s: float  # at the traveller's walking speed
    max_depth_m: float | None  # deepest water on the route; None if any part is of unknown depth
    max_depth_label: str  # e.g. "up to the ankle" for this traveller
    wading_length_m: float  # length under water deeper than 2 cm
    depth_weighted_wading_m2: float  # sum of wet length × depth, a simple exposure measure
    segments_over_limit: int  # pieces deeper than the traveller's limit, or of unknown depth
    detour_ratio: float | None  # length / reference length - 1 (e.g. vs the plain shortest route)


def route_metrics(
    route: Route, snapshot: HazardSnapshot, profile: TravellerProfile, reference_length_m: float | None = None
) -> RouteMetrics:
    deepest: float | None = 0.0
    wading = weighted = 0.0
    over = 0
    for seg in route.segments:
        cond = snapshot.condition(seg.source_edge_id)
        if cond.depth_m is None:
            deepest = None
            over += 1
            continue
        if deepest is not None:
            deepest = max(deepest, cond.depth_m)
        if cond.depth_m > profile.depth_limit_m:
            over += 1
        if cond.depth_m > DRY_DEPTH_M:
            wet = wet_length({"length_m": seg.length_m, "parent_length_m": seg.source_length_m}, cond)
            wading += wet
            weighted += wet * cond.depth_m
    detour = None
    if reference_length_m:
        detour = route.length_m / reference_length_m - 1
    return RouteMetrics(
        length_m=route.length_m,
        travel_time_s=route.length_m / profile.walking_speed_m_s,
        max_depth_m=deepest,
        max_depth_label=profile.describe_depth(deepest),
        wading_length_m=wading,
        depth_weighted_wading_m2=weighted,
        segments_over_limit=over,
        detour_ratio=detour,
    )
