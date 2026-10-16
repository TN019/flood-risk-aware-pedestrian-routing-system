"""Plan a whole trip under flood conditions, including what to do when no safe route exists.

``plan_trip`` combines:

1. **Where the traveller stands**: the water depth at the start, judged against their body
   (``risk.alerts``). Starting inside a building counts as sheltered.
2. **Three routes** to the destination (``routing.planning``).
3. When no route stays within their limit, or they are already in water over it:
   - **Downgrade**: the shallowest body-part limit that would make the trip possible (never above
     30 cm, never for wheelchair users), found with a minimax search, and the route under it.
   - **Refuge**: a nearby building to shelter in. From dry ground the route stays within the
     limit; from water over the limit it is the *safest* route (shallowest deepest point, then
     shortest), which may cross deep water and is marked as such.
4. **Emergency help** when the start is over 30 cm deep (more strongly above the knee and above
   half the traveller's height), or when no refuge can be reached at all. Only the request is
   produced here; sending it (e.g. alerting people nearby) is outside this package.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from shapely.geometry import Point

from floodroute.hazard import HazardSnapshot
from floodroute.places import Place
from floodroute.places.refuges import Refuge, RefugeIndex
from floodroute.risk import DEFAULT_ALPHA, HARD_LIMIT_M, BodyPart, TravellerProfile, risk_cost, walking_cost
from floodroute.risk.alerts import AlertLevel, alert_level
from floodroute.risk.model import source_edge_id
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
class Downgrade:
    body_part: BodyPart
    depth_limit_m: float
    required_depth_m: float  # the shallowest possible deepest point between start and destination
    option: RouteOption  # recommended route under the higher limit


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


def find_downgrade(
    router: Router,
    origin: Place,
    destination: Place,
    snapshot: HazardSnapshot,
    profile: TravellerProfile,
) -> Downgrade | None:
    if profile.uses_wheelchair:
        return None
    finder = MinimaxPathFinder(snapshot_depth(snapshot))
    try:
        route = router.route(origin.access_points, destination.access_points, walking_cost, path_finder=finder)
    except RoutingError:
        return None
    required = finder.last_bottleneck_m
    if required is None or required > HARD_LIMIT_M:
        return None
    for part in BodyPart:
        candidate = TravellerProfile(profile.height_m, part, walking_speed_m_s=profile.walking_speed_m_s)
        if candidate.depth_limit_m > profile.depth_limit_m and candidate.depth_limit_m >= required:
            # The least water that has to be faced, then the shortest way: matches ``required``.
            metrics = route_metrics(route, snapshot, candidate)
            return Downgrade(part, candidate.depth_limit_m, required, RouteOption("downgrade", route, metrics))
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
        finder = MinimaxPathFinder(snapshot_depth(snapshot))
        try:
            route = router.route(origin.access_points, points, walking_cost, path_finder=finder)
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

    downgrade = None
    if routes is not None and not safe and status.level <= AlertLevel.OVER_LIMIT:
        downgrade = find_downgrade(router, origin, destination, snapshot, profile)

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
    return TripPlan(status, routes, downgrade, refuge, emergency)
