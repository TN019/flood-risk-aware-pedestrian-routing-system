"""Plan a whole trip under flood conditions, including what to do when no safe route exists.

``plan_trip`` combines:

1. **Where the traveller stands**: the water depth at the start, judged against their body
   (``risk.alerts``). Starting inside a building counts as sheltered.
2. **Three routes** to the destination (``routing.planning``).
3. When no route stays within their limit, or they are already in water over it:
   - **Least water**: the route whose deepest point is shallowest (minimax search), how deep that
     point is and where, so the traveller can see why no route fits their limit.
   - **Downgrade**: the shallowest body-part limit that would make the trip possible (never above
     50 cm; for a mobility aid, the next level of the same device, never above its cap), found with
     a minimax search, and the route under it.
   - **Refuge**: a nearby building to shelter in. From dry ground the route stays within the
     limit; from water over the limit it is the *safest* route (shallowest deepest point, then
     shortest), which may cross deep water and is marked as such.
   Wheelchair users never use steps in any of these searches, so a refuge whose entrances can only
   be reached by steps is not offered to them.
4. **Emergency help** when the start is over 50 cm deep (more strongly above the knee and above
   half the traveller's height), or when no refuge can be reached at all. Only the request is
   produced here; sending it (e.g. alerting people nearby) is outside this package.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from shapely.geometry import Point

from floodroute.hazard import HazardSnapshot
from floodroute.places import Place
from floodroute.places.refuges import Refuge, RefugeIndex
from floodroute.risk import DEFAULT_ALPHA, BodyPart, TravellerProfile, risk_cost, walking_cost_for
from floodroute.risk.alerts import AlertLevel, alert_level
from floodroute.risk.model import edge_condition, source_edge_id
from floodroute.routing import Route, RouteMetrics, RouteOption, RoutePlan, Router, RoutingError, plan_routes
from floodroute.routing.metrics import route_metrics
from floodroute.routing.minimax import MinimaxPathFinder, snapshot_depth
from floodroute.routing.router import STANDING_TOLERANCE_M

ONLY_OPTION = "only option"


@dataclass(frozen=True)
class OriginStatus:
    level: AlertLevel
    depth_m: float | None
    depth_label: str
    sheltered: bool  # starting inside a building


@dataclass(frozen=True)
class LeastWater:
    """The way to the destination that faces the least water: the shallowest possible deepest point."""

    required_depth_m: float | None  # None when every way crosses water of unknown depth
    route: Route
    metrics: RouteMetrics
    deepest_at: Point  # metric CRS: where that deepest point is


@dataclass(frozen=True)
class Downgrade:
    """A higher limit that makes the trip possible: a body part, or a level of the traveller's
    mobility aid (then ``body_part`` is None and ``aid_level`` is set)."""

    body_part: BodyPart | None
    depth_limit_m: float
    required_depth_m: float  # the shallowest possible deepest point between start and destination
    option: RouteOption  # recommended route under the higher limit
    aid_level: int | None = None
    label: str = ""  # what the water reaches, e.g. "knee" or "below a 4-inch castor axle"


@dataclass(frozen=True)
class RefugeRoute:
    refuge: Refuge
    entrance_label: str
    route: Route
    metrics: RouteMetrics
    within_limit: bool


@dataclass(frozen=True)
class SosRequest:
    location: Point  # metric CRS
    depth_m: float | None
    depth_label: str
    level: AlertLevel
    depth_limit_m: float
    created_at: datetime


@dataclass(frozen=True)
class Emergency:
    advice: str  # "available" | "recommended" | "strongly recommended" | "only option"
    sos: SosRequest


@dataclass(frozen=True)
class TripPlan:
    origin: OriginStatus
    routes: RoutePlan | None  # None when the places are not connected at all
    downgrade: Downgrade | None
    refuge: RefugeRoute | None
    emergency: Emergency | None
    least_water: LeastWater | None = None  # only when no route stays within the limit

    @property
    def has_safe_route(self) -> bool:
        return self.routes is not None and self.routes.recommended.found


def origin_status(router: Router, origin: Place, snapshot: HazardSnapshot, profile: TravellerProfile) -> OriginStatus:
    if origin.building is not None:
        return OriginStatus(AlertLevel.OK, None, "indoors", sheltered=True)
    # Same rule as the router's access legs: at a corner, the traveller stands on the shallowest
    # of the footpaths that meet there.
    candidates = router.snap_candidates(origin.point)
    closest = candidates[0].distance_m + STANDING_TOLERANCE_M
    depths = [
        snapshot.condition(source_edge_id(router.graph.edges[c.edge])).depth_m
        for c in candidates
        if c.distance_m <= closest
    ]
    known = [d for d in depths if d is not None]
    depth = min(known) if known else None
    return OriginStatus(alert_level(depth, profile), depth, profile.describe_depth(depth), sheltered=False)


def find_least_water(
    router: Router,
    origin: Place,
    destination: Place,
    snapshot: HazardSnapshot,
    profile: TravellerProfile,
) -> LeastWater | None:
    finder = MinimaxPathFinder(snapshot_depth(snapshot, profile))
    try:
        route = router.route(
            origin.access_points, destination.access_points, walking_cost_for(profile), path_finder=finder
        )
    except RoutingError:
        return None
    required = finder.last_bottleneck_m
    if required is not None and math.isinf(required):
        required = None
    metrics = route_metrics(route, snapshot, profile)
    return LeastWater(required, route, metrics, _deepest_point(router, route, snapshot))


def _deepest_point(router: Router, route: Route, snapshot: HazardSnapshot) -> Point:
    """Middle of the route's deepest piece (unknown depth counts as deepest); for an access leg, the
    end of the route it belongs to."""
    deepest, where = -1.0, route.origin.point
    last = len(route.segments) - 1
    geometry = None
    for i, seg in enumerate(route.segments):
        data = {"edge_id": seg.source_edge_id, "length_m": seg.length_m, "standing_on": seg.standing_on}
        depth = edge_condition(snapshot, data).depth_m
        depth = math.inf if depth is None else depth
        if depth <= deepest:
            continue
        deepest = depth
        if seg.is_access:
            where = route.destination.point if i == last and i > 0 else route.origin.point
            continue
        if geometry is None:
            geometry = {d["edge_id"]: d["geometry"] for *_, d in router.graph.edges(data=True)}
        line = geometry.get(seg.source_edge_id)
        where = line.interpolate(0.5, normalized=True) if line is not None else where
    return where


def find_downgrade(least: LeastWater | None, profile: TravellerProfile, snapshot: HazardSnapshot) -> Downgrade | None:
    """The lowest higher limit that makes the trip possible, with the least-water route: the next
    body part for walkers, the next level of the same device for mobility aid users. Never above
    the traveller's hard limit (50 cm, or the device's cap)."""
    if least is None:
        return None
    required = least.required_depth_m
    if required is None or required > profile.hard_limit_m:
        return None
    if profile.uses_wheelchair:
        candidates = [
            (replace(profile, aid_level=i), None, i, level.label) for i, level in enumerate(profile.mobility_aid.levels)
        ]
    else:
        candidates = [
            (
                TravellerProfile(profile.height_m, part, walking_speed_m_s=profile.walking_speed_m_s),
                part,
                None,
                part.label,
            )
            for part in BodyPart
        ]
    for candidate, part, level, label in candidates:
        if candidate.depth_limit_m > profile.depth_limit_m and candidate.depth_limit_m >= required:
            # The least water that has to be faced, then the shortest way: matches ``required``.
            metrics = route_metrics(least.route, snapshot, candidate)
            option = RouteOption("downgrade", least.route, metrics)
            return Downgrade(part, candidate.depth_limit_m, required, option, level, label)
    return None


def find_refuge(
    router: Router,
    refuges: RefugeIndex,
    origin: Place,
    snapshot: HazardSnapshot,
    profile: TravellerProfile,
    level: AlertLevel,
    alpha: float,
) -> RefugeRoute | None:
    candidates = refuges.nearest(origin.point)
    if not candidates:
        return None
    owner = {}
    for refuge in candidates:
        for access in refuge.access:
            owner[(access.point.x, access.point.y)] = (refuge, access.label)
    points = [a.point for r in candidates for a in r.access]
    route = None
    if level == AlertLevel.OK:  # stay within the limit if at all possible
        try:
            route = router.route(origin.access_points, points, risk_cost(snapshot, profile, alpha=alpha))
        except RoutingError:
            route = None
    if route is None:  # already in deep water, or no dry way: the safest way out
        finder = MinimaxPathFinder(snapshot_depth(snapshot, profile))
        try:
            route = router.route(origin.access_points, points, walking_cost_for(profile), path_finder=finder)
        except RoutingError:
            return None
    refuge, label = owner[(route.destination.point.x, route.destination.point.y)]
    metrics = route_metrics(route, snapshot, profile)
    return RefugeRoute(refuge, label, route, metrics, within_limit=metrics.segments_over_limit == 0)


def plan_trip(
    router: Router,
    refuges: RefugeIndex,
    origin: Place,
    destination: Place,
    snapshot: HazardSnapshot,
    profile: TravellerProfile,
    alpha: float = DEFAULT_ALPHA,
    now: datetime | None = None,
) -> TripPlan:
    status = origin_status(router, origin, snapshot, profile)
    try:
        routes = plan_routes(router, origin.access_points, destination.access_points, snapshot, profile, alpha)
    except RoutingError:
        routes = None
    safe = routes is not None and routes.recommended.found

    least = None
    if routes is not None and not safe:
        least = find_least_water(router, origin, destination, snapshot, profile)
    downgrade = None
    if status.level <= AlertLevel.OVER_LIMIT:
        downgrade = find_downgrade(least, profile, snapshot)

    refuge = None
    if (not safe or status.level >= AlertLevel.OVER_LIMIT) and not status.sheltered:
        refuge = find_refuge(router, refuges, origin, snapshot, profile, status.level, alpha)

    advice = status.level.emergency_advice
    if not status.sheltered and not safe and refuge is None:
        advice = ONLY_OPTION
    emergency = None
    if advice is not None:
        sos = SosRequest(
            origin.point,
            status.depth_m,
            status.depth_label,
            status.level,
            profile.depth_limit_m,
            now or datetime.now(UTC),
        )
        emergency = Emergency(advice, sos)
    return TripPlan(status, routes, downgrade, refuge, emergency, least)
