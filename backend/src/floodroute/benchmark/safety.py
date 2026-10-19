"""The safety routes give, what it costs, and rerouting while a flood rises.

``safety_cost``: random trips at every flood level for several travellers: how many have a route
within the limit, what the recommended route avoids compared with the plain shortest way and how much
longer it is, and what is offered when no route fits. It also times every plan.

``rising_flood``: a traveller walks while the flood level rises on a schedule; at every rise the trip
is planned again from where they are and they follow the new advice. Each part of a route is walked
under the level it was planned for, so no metre should be walked over the limit on a route given as
within it. A route may run into the network's margin outside Southbank, where no trip can be planned
(starts must lie inside); a rise there leaves the traveller on the route they have, under the new
level, and that is counted separately.
"""

from __future__ import annotations

import math
import time
from collections import Counter

from shapely.geometry import LineString, Point

from floodroute.benchmark.world import World, quantile
from floodroute.hazard import HazardSnapshot
from floodroute.places import Place
from floodroute.risk import BodyPart, MobilityAid, TravellerProfile
from floodroute.risk.alerts import AlertLevel
from floodroute.risk.model import edge_condition
from floodroute.routing import Route, RoutingError
from floodroute.trip import TripPlan, plan_trip

ADULT, CHILD = 1.70, 1.20
TRAVELLERS = {
    "adult, ankle": TravellerProfile(ADULT, BodyPart.ANKLE),
    "adult, mid calf": TravellerProfile(ADULT, BodyPart.MID_CALF),
    "child, mid calf": TravellerProfile(CHILD, BodyPart.MID_CALF),
    "manual wheelchair, 5 cm": TravellerProfile(ADULT, mobility_aid=MobilityAid.MANUAL_WHEELCHAIR, aid_level=1),
}
RISING = (("light-flooding", 0.0), ("moderate-flooding", 240.0), ("heavy-flooding", 480.0))


def _over_limit_m(
    route: Route, snapshot: HazardSnapshot, profile: TravellerProfile, from_m: float = 0.0, upto_m: float = math.inf
) -> float:
    """Metres of the route between ``from_m`` and ``upto_m`` that lie on water deeper than the limit
    or of unknown depth."""
    total, walked = 0.0, 0.0
    for seg in route.segments:
        if walked >= upto_m:
            break
        part = min(walked + seg.length_m, upto_m) - max(walked, from_m)
        if part <= 0:
            walked += seg.length_m
            continue
        cond = edge_condition(
            snapshot, {"edge_id": seg.source_edge_id, "length_m": seg.length_m, "standing_on": seg.standing_on}
        )
        if cond.depth_m is None or cond.depth_m > profile.depth_limit_m:
            total += part
        walked += seg.length_m
    return total


def _offered(plan: TripPlan) -> str:
    """What a trip without a route within the limit is offered, most hopeful first."""
    if plan.routes is None:
        return "not connected"
    if plan.downgrade is not None:
        return "higher limit"
    if plan.refuge is not None:
        return "shelter"
    if plan.origin.sheltered:
        return "stay inside"
    if plan.emergency is not None:
        return "emergency help"
    return "nothing"


def safety_cost(world: World, trips: list[tuple[Place, Place]], levels: list[str] | None = None) -> dict:
    out: dict = {"trips": len(trips), "levels": {}, "plan_ms": {}}
    for level in levels or [s for s in world.snapshots if s != "normal"]:
        snap = world.snapshots[level]
        by_traveller, times = {}, []
        for name, profile in TRAVELLERS.items():
            safe = over_limit_routes = 0
            detours, avoided, short_deep, rec_deep = [], [], [], []
            offered: Counter = Counter()
            for origin, destination in trips:
                start = time.perf_counter()
                plan = plan_trip(world.router, world.refuges, origin, destination, snap, profile)
                times.append((time.perf_counter() - start) * 1000)
                if not plan.has_safe_route:
                    offered[_offered(plan)] += 1
                    continue
                safe += 1
                rec, short = plan.routes.recommended, plan.routes.shortest
                over_limit_routes += _over_limit_m(rec.route, snap, profile) > 0
                if short.found and _over_limit_m(short.route, snap, profile) > 0:
                    detours.append(rec.route.length_m / short.route.length_m - 1)
                    avoided.append(_over_limit_m(short.route, snap, profile))
                    short_deep.append(short.metrics.max_depth_m if short.metrics.max_depth_m is not None else math.inf)
                    rec_deep.append(rec.metrics.max_depth_m or 0.0)
            by_traveller[name] = {
                "with_route": safe,
                "recommended_over_limit": over_limit_routes,
                "shortest_unsafe": len(detours),
                "detour_median": quantile(detours, 0.5),
                "detour_p90": quantile(detours, 0.9),
                "over_limit_avoided_m_median": quantile(avoided, 0.5),
                "shortest_deepest_median_m": quantile([d for d in short_deep if math.isfinite(d)], 0.5),
                "shortest_unknown_depth": sum(1 for d in short_deep if not math.isfinite(d)),
                "recommended_deepest_median_m": quantile(rec_deep, 0.5),
                "without_route": dict(offered),
            }
        out["levels"][level] = {"title": world.titles[level], "travellers": by_traveller}
        out["plan_ms"][level] = {"median": quantile(times, 0.5), "p95": quantile(times, 0.95), "plans": len(times)}
    return out


def _point_at(route: Route, d: float) -> Point:
    """Where a traveller is after walking ``d`` metres of the route."""
    first = route.segments[0] if route.segments else None
    lead = first.length_m if first is not None and first.is_access else 0.0
    if d <= lead and lead > 0:
        return LineString([route.origin.point, route.origin.snapped]).interpolate(d)
    return route.geometry.interpolate(min(max(d - lead, 0.0), route.geometry.length))


def rising_flood(
    world: World,
    trips: list[tuple[Place, Place]],
    traveller: str = "adult, mid calf",
    schedule: tuple[tuple[str, float], ...] = RISING,
) -> dict:
    profile = TRAVELLERS[traveller]
    outcomes: Counter = Counter()
    violations_m = escape_m = outside_m = 0.0
    reroutes, rerouted_trips, caught, outside = 0, 0, 0, 0
    extra = []
    for origin, destination in trips:
        t, k, here, planned_first, walked_total, trip_reroutes = 0.0, 0, origin, None, 0.0, 0
        route, given_safe, goal, offset = None, False, "", 0.0
        while True:
            snap = world.snapshots[schedule[k][0]]
            try:
                plan = plan_trip(world.router, world.refuges, here, destination, snap, profile)
            except RoutingError:
                if route is None:
                    raise
                plan = None  # outside Southbank: no new plan, so they keep to the route they have
                outside += 1
            if plan is not None:
                if trip_reroutes and plan.origin.level > AlertLevel.OK:
                    caught += 1  # the water rose over the limit where they stand
                if plan.has_safe_route:
                    route, given_safe, goal = plan.routes.recommended.route, True, "arrived"
                elif plan.refuge is not None:
                    route, given_safe, goal = plan.refuge.route, plan.refuge.within_limit, "at a shelter"
                else:
                    outcomes[_offered(plan)] += 1
                    break
                offset = 0.0
                if planned_first is None:
                    planned_first = route.length_m
            next_rise = schedule[k + 1][1] if k + 1 < len(schedule) else math.inf
            walk = min(route.length_m - offset, (next_rise - t) * profile.walking_speed_m_s)
            over = _over_limit_m(route, snap, profile, offset, offset + walk)
            if plan is None:
                outside_m += over
            elif given_safe:
                violations_m += over
            else:
                escape_m += over  # the safest way out of water already over the limit
            walked_total += walk
            offset += walk
            if offset >= route.length_m - 1e-9:
                outcomes[goal] += 1
                if goal == "arrived":
                    extra.append(walked_total / planned_first - 1)
                break
            t, k = next_rise, k + 1
            trip_reroutes += 1
            here = world.resolver.resolve(_point_at(route, offset), "here", role="origin")
        reroutes += trip_reroutes
        rerouted_trips += trip_reroutes > 0
    return {
        "trips": len(trips),
        "traveller": traveller,
        "schedule": [{"level": world.titles[lv], "from_s": s} for lv, s in schedule],
        "violations_m": violations_m,
        "escape_over_limit_m": escape_m,
        "reroutes": reroutes,
        "trips_rerouted": rerouted_trips,
        "caught_by_rising_water": caught,
        "not_replanned_outside_area": outside,
        "over_limit_outside_area_m": outside_m,
        "outcomes": dict(outcomes),
        "extra_walk_median": quantile(extra, 0.5),
        "extra_walk_p90": quantile(extra, 0.9),
    }
