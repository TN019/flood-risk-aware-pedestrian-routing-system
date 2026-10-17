"""Wheelchair users never use steps; everyone else may."""

import math

import geopandas as gpd
import networkx as nx
import pytest
from shapely.geometry import LineString, Point, box

from floodroute import config
from floodroute.hazard import DRY, EdgeCondition, HazardSnapshot
from floodroute.places import PlaceResolver
from floodroute.places.refuges import RefugeIndex
from floodroute.risk import BodyPart, TravellerProfile, can_use, risk_cost, walking_cost, walking_cost_for
from floodroute.risk.alerts import AlertLevel
from floodroute.routing import Router, plan_routes
from floodroute.routing.minimax import snapshot_depth
from floodroute.routing.planning import NO_STEP_FREE_ROUTE
from floodroute.trip import find_refuge, plan_trip

ADULT = 1.70
WALKER = TravellerProfile(ADULT, BodyPart.ANKLE)
CHAIR = TravellerProfile(ADULT, BodyPart.MID_CALF, uses_wheelchair=True)
DRY_SNAPSHOT = HazardSnapshot("dry", default=DRY)
STEPS = {"length_m": 20.0, "cost_factor": 1.0, "edge_id": "s", "is_steps": True}
PATH = {"length_m": 20.0, "cost_factor": 1.0, "edge_id": "p", "is_steps": False}
A, B = (0.0, 0.0), (300.0, 0.0)


def three_streets(steps=()):
    """Three ways from A to B: 300 m straight (e0), 350 m (e1, e2) and 420 m (e3, e4)."""
    g = nx.Graph(crs=config.METRIC_CRS)
    xy = {"A": A, "B": B, "M2": (150.0, math.sqrt(175**2 - 150**2)), "M3": (150.0, math.sqrt(210**2 - 150**2))}
    for n, (x, y) in xy.items():
        g.add_node(n, x=x, y=y, kind="junction", in_study_area=True)
    for i, (u, v) in enumerate((("A", "B"), ("A", "M2"), ("M2", "B"), ("A", "M3"), ("M3", "B"))):
        geom = LineString([xy[u], xy[v]])
        eid = f"e{i}"
        g.add_edge(
            u,
            v,
            geometry=geom,
            length_m=geom.length,
            edge_id=eid,
            cost_factor=1.0,
            in_study_area=True,
            is_steps=eid in steps,
        )
    return g


def plan(profile, steps=(), snapshot=DRY_SNAPSHOT):
    return plan_routes(Router(three_streets(steps)), Point(*A), Point(*B), snapshot, profile)


def test_steps_are_unusable_for_wheelchair_users_only():
    assert can_use(WALKER, STEPS) and can_use(CHAIR, PATH) and not can_use(CHAIR, STEPS)
    assert walking_cost_for(WALKER) is walking_cost
    assert walking_cost_for(CHAIR)(0, 1, STEPS) is None
    assert walking_cost_for(CHAIR)(0, 1, PATH) == 20.0
    assert risk_cost(DRY_SNAPSHOT, CHAIR)(0, 1, STEPS) is None
    assert risk_cost(DRY_SNAPSHOT, WALKER)(0, 1, STEPS) == 20.0
    assert snapshot_depth(DRY_SNAPSHOT, CHAIR)(0, 1, STEPS) is None
    assert snapshot_depth(DRY_SNAPSHOT, WALKER)(0, 1, STEPS) == 0.0


def test_walkers_still_take_the_steps():
    p = plan(WALKER, steps=("e0",))
    assert {round(o.route.length_m, 6) for o in p.options} == {300.0}
    assert all(o.route.uses_steps for o in p.options)
    assert not p.step_free and not p.steps_avoided


def test_wheelchair_users_get_the_step_free_detour_on_every_route():
    p = plan(CHAIR, steps=("e0",))
    assert {round(o.route.length_m, 6) for o in p.options} == {350.0}
    assert not any(o.route.uses_steps for o in p.options)
    assert p.step_free and p.steps_avoided
    assert p.shortest.metrics.detour_ratio == 0  # measured against the step-free shortest


def test_wheelchair_users_get_no_route_when_every_way_has_steps():
    p = plan(CHAIR, steps=("e0", "e1", "e4"))
    assert not any(o.found for o in p.options)
    assert all(o.error == NO_STEP_FREE_ROUTE for o in p.options)
    assert plan(WALKER, steps=("e0", "e1", "e4")).recommended.route.length_m == pytest.approx(300)


def test_step_free_route_within_the_limit_is_reported_as_such():
    flood = HazardSnapshot("f", conditions={"e1": EdgeCondition(0.10)}, default=DRY)
    p = plan(CHAIR, steps=("e0", "e4"), snapshot=flood)  # dry ways have steps; the step-free one is wet
    assert p.shortest.route.length_m == pytest.approx(350) and not p.shortest.route.uses_steps
    assert not p.recommended.found and "step-free" in p.recommended.error


# A ladder: low street y=0 (e0: x 0..150, e1: x 150..300), connectors at x=0 (e2) and x=300 (e4),
# high street y=100 (e3, steps). "North" has its door on the stepped high street, "South" on e1.
def ladder():
    g = nx.Graph(crs=config.METRIC_CRS)
    xy = {1: (0, 0), 2: (150, 0), 3: (300, 0), 4: (0, 100), 5: (300, 100)}
    for n, (x, y) in xy.items():
        g.add_node(n, x=x, y=y, kind="junction", in_study_area=True)
    for i, (u, v) in enumerate(((1, 2), (2, 3), (1, 4), (4, 5), (5, 3))):
        geom = LineString([xy[u], xy[v]])
        g.add_edge(
            u,
            v,
            geometry=geom,
            length_m=geom.length,
            edge_id=f"e{i}",
            cost_factor=1.0,
            in_study_area=True,
            is_steps=i == 3,
        )
    router = Router(g)
    buildings = gpd.GeoDataFrame(
        {"name": ["North", "South"], "geometry": [box(20, 110, 60, 140), box(200, -40, 240, -10)]},
        crs=config.METRIC_CRS,
    )
    doors = gpd.GeoDataFrame(
        {"element": "node", "id": [0, 1], "entrance": "main", "geometry": [Point(40, 110), Point(220, -10)]},
        crs=config.METRIC_CRS,
    )
    resolver = PlaceResolver(buildings, doors, router.footpaths)
    origin = resolver.resolve(Point(75, 0), "origin", role="origin")
    return router, resolver, RefugeIndex(resolver), origin


def test_refuges_reached_only_by_steps_are_not_offered_to_wheelchair_users():
    router, _, refuges, origin = ladder()
    snap = HazardSnapshot("f", conditions={"e1": EdgeCondition(0.10)}, default=DRY)
    walker = find_refuge(router, refuges, origin, snap, WALKER, AlertLevel.OK, 2.0)
    assert walker.refuge.name == "North" and walker.within_limit and walker.route.uses_steps
    chair = find_refuge(router, refuges, origin, snap, CHAIR, AlertLevel.OK, 2.0)
    assert chair.refuge.name == "South" and not chair.within_limit and not chair.route.uses_steps  # via 10 cm


def test_no_wheelchair_route_in_a_trip_uses_steps():
    router, resolver, refuges, origin = ladder()
    snap = HazardSnapshot("f", conditions={"e1": EdgeCondition(0.10)}, default=DRY)
    t = plan_trip(router, refuges, origin, resolver.resolve(Point(300, 50), "destination"), snap, CHAIR)
    assert not t.has_safe_route and t.routes.step_free
    routes = [o.route for o in t.routes.options if o.found] + [t.refuge.route, t.least_water.route]
    assert len(routes) == 3 and not any(r.uses_steps for r in routes)


def test_an_access_leg_cannot_skip_a_short_flight_of_steps():
    """A 6 m flight S0–S1 between two footpaths, and an 86 m step-free way round it. From the bottom
    of the flight, the footpath at the top is only 6 m away in a straight line."""
    g = nx.Graph(crs=config.METRIC_CRS)
    xy = {"P": (-100, 0), "S0": (0, 0), "S1": (6, 0), "Q": (106, 0), "U": (0, 40), "V": (6, 40)}
    for n, (x, y) in xy.items():
        g.add_node(n, x=x, y=y, kind="junction", in_study_area=True)
    for i, (u, v) in enumerate((("P", "S0"), ("S0", "S1"), ("S1", "Q"), ("S0", "U"), ("U", "V"), ("V", "S1"))):
        geom = LineString([xy[u], xy[v]])
        g.add_edge(
            u,
            v,
            geometry=geom,
            length_m=geom.length,
            edge_id=f"e{i}",
            cost_factor=1.0,
            in_study_area=True,
            is_steps=i == 1,
        )
    router = Router(g)
    walker = plan_routes(router, Point(0, 0), Point(6, 0), DRY_SNAPSHOT, WALKER)
    assert walker.recommended.route.length_m == pytest.approx(6) and walker.recommended.route.uses_steps
    chair = plan_routes(router, Point(0, 0), Point(6, 0), DRY_SNAPSHOT, CHAIR)
    assert {round(o.route.length_m, 6) for o in chair.options} == {86.0}
    assert not any(o.route.uses_steps for o in chair.options)
    # Legs that only meet the flight at its top or bottom are not steps.
    assert not router.passes_steps(LineString([(-5, -5), (0, 0)]))
    assert not router.passes_steps(LineString([(6, 10), (6, 0)]))
    assert router.passes_steps(LineString([(3, -5), (3, 5)]))  # across the middle


def test_an_access_leg_cannot_skip_a_flight_that_turns_back():
    """A 10 m flight that climbs north and comes back, so its bottom S0 and top S1 are 2 m apart, and
    a 62 m step-free way round to the south."""
    g = nx.Graph(crs=config.METRIC_CRS)
    xy = {"P": (-100, 0), "S0": (0, 0), "S1": (2, 0), "Q": (102, 0), "U": (0, -30), "V": (2, -30)}
    for n, (x, y) in xy.items():
        g.add_node(n, x=x, y=y, kind="junction", in_study_area=True)
    flight = LineString([(0, 0), (0, 4), (2, 4), (2, 0)])
    edges = (("P", "S0"), ("S0", "S1"), ("S1", "Q"), ("S0", "U"), ("U", "V"), ("V", "S1"))
    for i, (u, v) in enumerate(edges):
        geom = flight if i == 1 else LineString([xy[u], xy[v]])
        g.add_edge(
            u,
            v,
            geometry=geom,
            length_m=geom.length,
            edge_id=f"e{i}",
            cost_factor=1.0,
            in_study_area=True,
            is_steps=i == 1,
        )
    router = Router(g)
    assert router.passes_steps(LineString([(0, 0), (2, 0)]))
    chair = plan_routes(router, Point(0, 0), Point(2, 0), DRY_SNAPSHOT, CHAIR)
    assert {round(o.route.length_m, 6) for o in chair.options} == {62.0}
    assert not any(o.route.uses_steps for o in chair.options)
