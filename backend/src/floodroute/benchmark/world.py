"""The Southbank network, places and flood scenarios, loaded once for every benchmark."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import geopandas as gpd
import networkx as nx
from shapely.geometry import Point

from floodroute import config
from floodroute.hazard import HazardSnapshot
from floodroute.places import Place, PlaceResolver
from floodroute.places.refuges import RefugeIndex
from floodroute.routing import Router, RoutingError


@dataclass
class World:
    graph: nx.Graph
    router: Router
    resolver: PlaceResolver
    refuges: RefugeIndex
    snapshots: dict[str, HazardSnapshot]  # by scenario id, from normal to extreme
    titles: dict[str, str]


def load_world() -> World:
    from floodroute.hazard.catalog import list_scenarios, load_hazard
    from floodroute.network import load_graph

    g = load_graph(config.PROCESSED_NETWORK_PATH)
    router = Router(g)
    places = config.PROCESSED_PLACES_PATH
    resolver = PlaceResolver(
        gpd.read_file(places, layer="buildings"), gpd.read_file(places, layer="entrances"), router.footpaths
    )
    refuges = RefugeIndex(resolver, g.graph["study_area"].buffer(g.graph["buffer_m"]))
    scenarios = sorted(list_scenarios(), key=lambda s: s.order)
    snapshots = {s.id: load_hazard(s).snapshot(g) for s in scenarios}
    return World(g, router, resolver, refuges, snapshots, {s.id: s.title for s in scenarios})


def random_trips(world: World, n: int, seed: int, min_m: float = 300, max_m: float = 1500) -> list[tuple[Place, Place]]:
    """Trips between random points inside Southbank, starting outdoors (not inside a building) and
    connected on the network."""
    area = world.graph.graph["study_area"]
    minx, miny, maxx, maxy = area.bounds
    rng = random.Random(seed)
    trips: list[tuple[Place, Place]] = []
    while len(trips) < n:
        a, b = (Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy)) for _ in range(2))
        if not (area.contains(a) and area.contains(b)) or not min_m <= a.distance(b) <= max_m:
            continue
        origin = world.resolver.resolve(a, "start", role="origin")
        if origin.building is not None:
            continue
        try:
            world.router.route(a, b)
        except RoutingError:
            continue
        trips.append((origin, world.resolver.resolve(b, "destination")))
    return trips


def quantile(values: list[float], q: float) -> float | None:
    """The q-quantile (0–1) by linear interpolation; None for no values."""
    if not values:
        return None
    s = sorted(values)
    pos = (len(s) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)
