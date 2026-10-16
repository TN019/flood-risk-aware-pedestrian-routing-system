"""Routing: joining arbitrary points to the network, searching for cheapest paths, and planning
walks under flood conditions."""

from floodroute.routing.dijkstra import Dijkstra, SearchResult
from floodroute.routing.metrics import RouteMetrics, route_metrics
from floodroute.routing.pathfinding import NetworkXDijkstra, NoPathError, PathFinder
from floodroute.routing.planning import RECOMMENDED, SAFE_SHORTEST, SHORTEST, RouteOption, RoutePlan, plan_routes
from floodroute.routing.router import Route, Router, RouteSegment, RoutingError, Snap

__all__ = [
    "RECOMMENDED",
    "SAFE_SHORTEST",
    "SHORTEST",
    "Dijkstra",
    "NetworkXDijkstra",
    "NoPathError",
    "PathFinder",
    "Route",
    "RouteMetrics",
    "RouteOption",
    "RoutePlan",
    "RouteSegment",
    "Router",
    "RoutingError",
    "SearchResult",
    "Snap",
    "plan_routes",
    "route_metrics",
]
