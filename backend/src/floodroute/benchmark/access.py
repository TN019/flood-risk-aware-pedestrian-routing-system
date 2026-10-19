"""Step-free connectivity between buildings under normal conditions.

For random pairs of buildings inside Southbank: the walking route, and the step-free route a manual
wheelchair user gets. A step-free route is also a walking route, so it can never be shorter, and it
must never use steps.
"""

from __future__ import annotations

import random

from floodroute.benchmark.world import World, quantile
from floodroute.risk import MobilityAid, TravellerProfile, walking_cost_for
from floodroute.routing import RoutingError

TOLERANCE = 1e-6  # metres


def step_free_pairs(world: World, n: int = 300, seed: int = 2026, min_m: float = 200, max_m: float = 1500) -> dict:
    area = world.graph.graph["study_area"]
    buildings = [g for g in world.resolver.buildings.geometry if area.contains(g.representative_point())]
    walker = TravellerProfile(1.70)
    chair = TravellerProfile(1.70, mobility_aid=MobilityAid.MANUAL_WHEELCHAIR)
    walk_cost, chair_cost = walking_cost_for(walker), walking_cost_for(chair)
    rng = random.Random(seed)
    out = {"pairs": 0, "walking_route": 0, "step_free_route": 0, "step_free_using_steps": 0, "step_free_shorter": 0}
    ratios = []
    tries = 0
    while out["pairs"] < n and tries < n * 50:
        tries += 1
        a, b = rng.sample(buildings, 2)
        pa, pb = a.representative_point(), b.representative_point()
        if not min_m <= pa.distance(pb) <= max_m:
            continue
        origin = world.resolver.resolve(pa, "a", role="origin")
        destination = world.resolver.resolve(pb, "b")
        try:
            walking = world.router.route(origin.access_points, destination.access_points, walk_cost)
        except RoutingError:
            continue  # not connected on foot either: outside what this measures
        out["pairs"] += 1
        out["walking_route"] += 1
        try:
            step_free = world.router.route(origin.access_points, destination.access_points, chair_cost)
        except RoutingError:
            continue
        out["step_free_route"] += 1
        out["step_free_using_steps"] += step_free.uses_steps
        out["step_free_shorter"] += step_free.length_m < walking.length_m - TOLERANCE
        ratios.append(step_free.length_m / walking.length_m)
    out["longer_median"] = quantile([r - 1 for r in ratios], 0.5)
    out["longer_p90"] = quantile([r - 1 for r in ratios], 0.9)
    out["longer_max"] = max((r - 1 for r in ratios), default=None)
    out["same_length"] = sum(1 for r in ratios if abs(r - 1) <= 1e-9)
    return out
