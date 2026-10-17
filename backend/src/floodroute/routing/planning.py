"""Plan a walk under flood conditions as three routes that separate what each rule contributes.

- ``shortest``       plain walking cost, ignoring the flood: what an ordinary navigation app does
- ``safe_shortest``  shortest using only edges within the traveller's limit (safety filter, α = 0)
- ``recommended``    safety filter plus risk weighting (α > 0): may detour further to stay drier

Comparing ``shortest`` with ``safe_shortest`` shows what excluding unsafe water changes; comparing
``safe_shortest`` with ``recommended`` shows what weighting the remaining risk changes.

All three leave out edges the traveller cannot use at all (steps, for wheelchair users), so for
them ``shortest`` is the shortest step-free way.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from shapely.geometry import Point

from floodroute.hazard import HazardSnapshot
from floodroute.risk import (
    DEFAULT_ALPHA,
    DepthRelativeRisk,
    RiskModel,
    TravellerProfile,
    risk_cost,
    walking_cost_for,
)
from floodroute.risk.model import source_edge_id
from floodroute.routing.metrics import RouteMetrics, route_metrics
from floodroute.routing.router import Route, Router, RoutingError

SHORTEST, SAFE_SHORTEST, RECOMMENDED = "shortest", "safe_shortest", "recommended"
NO_STEP_FREE_ROUTE = "No step-free route connects these places."


@dataclass(frozen=True)
class RouteOption:
    kind: str
    route: Route | None
    metrics: RouteMetrics | None
    error: str | None = None

    @property
    def found(self) -> bool:
        return self.route is not None


@dataclass(frozen=True)
class RoutePlan:
    shortest: RouteOption
    safe_shortest: RouteOption
    recommended: RouteOption
    alpha: float
    blocked_edges: int  # network edges over this traveller's limit under these conditions
    step_free: bool = False  # the traveller cannot use steps, so no route uses them
    steps_avoided: bool = False  # the plain shortest way uses steps this traveller cannot use

    @property
    def options(self) -> tuple[RouteOption, RouteOption, RouteOption]:
        return (self.shortest, self.safe_shortest, self.recommended)


def plan_routes(
    router: Router,
    origin: Point | Sequence[Point],
    destination: Point | Sequence[Point],
    snapshot: HazardSnapshot,
    profile: TravellerProfile,
    alpha: float = DEFAULT_ALPHA,
    model: RiskModel | None = None,
) -> RoutePlan:
    """Raises ``RoutingError`` only when the two places are not connected at all; when water or
    steps are the obstacle, the options carry an ``error`` instead of a route."""
    model = model or DepthRelativeRisk()
    blocked = sum(
        1
        for *_, d in router.graph.edges(data=True)
        if model.edge_risk(snapshot.condition(source_edge_id(d)), profile) is None
    )
    step_free = profile.uses_wheelchair
    steps_avoided = step_free and router.route(origin, destination).uses_steps
    try:
        shortest = router.route(origin, destination, walking_cost_for(profile))
    except RoutingError:
        if not step_free:
            raise
        none = [RouteOption(kind, None, None, NO_STEP_FREE_ROUTE) for kind in (SHORTEST, SAFE_SHORTEST, RECOMMENDED)]
        return RoutePlan(*none, alpha=alpha, blocked_edges=blocked, step_free=True, steps_avoided=True)
    reference = shortest.length_m

    def option(kind: str, cost) -> RouteOption:
        try:
            route = router.route(origin, destination, cost)
        except RoutingError:
            limit_cm = profile.depth_limit_m * 100
            way = "step-free route" if step_free else "route"
            return RouteOption(kind, None, None, f"No {way} keeps you within your limit ({limit_cm:.0f} cm).")
        return RouteOption(kind, route, route_metrics(route, snapshot, profile, reference))

    return RoutePlan(
        shortest=RouteOption(SHORTEST, shortest, route_metrics(shortest, snapshot, profile, reference)),
        safe_shortest=option(SAFE_SHORTEST, risk_cost(snapshot, profile, model, alpha=0.0)),
        recommended=option(RECOMMENDED, risk_cost(snapshot, profile, model, alpha=alpha)),
        alpha=alpha,
        blocked_edges=blocked,
        step_free=step_free,
        steps_avoided=steps_avoided,
    )
