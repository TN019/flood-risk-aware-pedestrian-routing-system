"""Plan a walk under flood conditions as three routes that separate what each rule contributes.

- ``shortest``       plain walking cost, ignoring the flood: what an ordinary navigation app does
- ``safe_shortest``  shortest using only edges within the traveller's limit (safety filter, α = 0)
- ``recommended``    safety filter plus risk weighting (α > 0): may detour further to stay drier

Comparing ``shortest`` with ``safe_shortest`` shows what excluding unsafe water changes; comparing
``safe_shortest`` with ``recommended`` shows what weighting the remaining risk changes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from shapely.geometry import Point

from floodroute.hazard import HazardSnapshot
from floodroute.risk import DEFAULT_ALPHA, DepthRelativeRisk, RiskModel, TravellerProfile, risk_cost
from floodroute.risk.model import source_edge_id
from floodroute.routing.metrics import RouteMetrics, route_metrics
from floodroute.routing.router import Route, Router, RoutingError

SHORTEST, SAFE_SHORTEST, RECOMMENDED = "shortest", "safe_shortest", "recommended"


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
    blocked_edges: int  # network edges this traveller may not use under these conditions

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
    """Raises ``RoutingError`` only when the two places are not connected at all; when water is
    the obstacle, the safe and recommended options carry an ``error`` instead of a route."""
    model = model or DepthRelativeRisk()
    shortest = router.route(origin, destination)
    reference = shortest.length_m

    def option(kind: str, cost) -> RouteOption:
        try:
            route = router.route(origin, destination, cost)
        except RoutingError:
            limit_cm = profile.depth_limit_m * 100
            return RouteOption(kind, None, None, f"No route keeps you within your limit ({limit_cm:.0f} cm).")
        return RouteOption(kind, route, route_metrics(route, snapshot, profile, reference))

    blocked = sum(
        1
        for *_, d in router.graph.edges(data=True)
        if model.edge_risk(snapshot.condition(source_edge_id(d)), profile) is None
    )
    return RoutePlan(
        shortest=RouteOption(SHORTEST, shortest, route_metrics(shortest, snapshot, profile, reference)),
        safe_shortest=option(SAFE_SHORTEST, risk_cost(snapshot, profile, model, alpha=0.0)),
        recommended=option(RECOMMENDED, risk_cost(snapshot, profile, model, alpha=alpha)),
        alpha=alpha,
        blocked_edges=blocked,
    )
