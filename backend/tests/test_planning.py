import math

import networkx as nx
import pytest
from shapely.geometry import LineString, Point

from floodroute import config
from floodroute.hazard import DRY, EdgeCondition, HazardSnapshot
from floodroute.risk import BodyPart, TravellerProfile
from floodroute.routing import Router, RoutingError, plan_routes

ADULT = 1.70
A, B = (0.0, 0.0), (300.0, 0.0)


def three_streets():
    """Three ways from A to B: a 300 m straight street (e0), a 350 m street (e1, e2) and a 420 m
    street (e3, e4), the latter two bending north through a midpoint."""
    g = nx.Graph(crs=config.METRIC_CRS)
    mid2 = (150.0, math.sqrt(175**2 - 150**2))
    mid3 = (150.0, math.sqrt(210**2 - 150**2))
    xy = {"A": A, "B": B, "M2": mid2, "M3": mid3}
    for n, (x, y) in xy.items():
        g.add_node(n, x=x, y=y, kind="junction", in_study_area=True)
    for i, (u, v) in enumerate((("A", "B"), ("A", "M2"), ("M2", "B"), ("A", "M3"), ("M3", "B"))):
        geom = LineString([xy[u], xy[v]])
        g.add_edge(u, v, geometry=geom, length_m=geom.length, edge_id=f"e{i}", cost_factor=1.0, in_study_area=True)
    return g


# Deep water on the shortest street, shallow water on the middle one, the long one dry.
FLOOD = HazardSnapshot(
    "test",
    conditions={"e0": EdgeCondition(0.10), "e1": EdgeCondition(0.05), "e2": EdgeCondition(0.05)},
    default=DRY,
)


def plan(profile, alpha=2.0, snapshot=FLOOD):
    return plan_routes(Router(three_streets()), Point(*A), Point(*B), snapshot, profile, alpha)


def test_three_routes_separate_filtering_from_weighting():
    p = plan(TravellerProfile(ADULT, BodyPart.ANKLE))  # limit 6.6 cm
    assert p.shortest.route.length_m == pytest.approx(300)  # through 10 cm water
    assert p.shortest.metrics.segments_over_limit > 0
    assert p.safe_shortest.route.length_m == pytest.approx(350)  # filter only: shallow street
    assert p.recommended.route.length_m == pytest.approx(420)  # weighting: the dry street
    assert p.recommended.metrics.wading_length_m == 0
    assert p.recommended.metrics.detour_ratio == pytest.approx(0.4)
    assert p.blocked_edges == 1  # e0


def test_low_alpha_keeps_the_shallow_street():
    p = plan(TravellerProfile(ADULT, BodyPart.ANKLE), alpha=0.1)
    assert p.recommended.route.length_m == pytest.approx(350)


def test_dry_conditions_make_all_three_identical():
    p = plan(TravellerProfile(ADULT, BodyPart.NO_WADING), snapshot=HazardSnapshot("dry", default=DRY))
    lengths = {round(o.route.length_m, 6) for o in p.options}
    assert lengths == {300.0} and p.blocked_edges == 0


def test_no_safe_route_is_reported_per_option():
    deep = HazardSnapshot("deep", conditions={f"e{i}": EdgeCondition(0.4) for i in range(5)}, default=DRY)
    p = plan(TravellerProfile(ADULT, BodyPart.MID_CALF), snapshot=deep)
    assert p.shortest.found
    assert not p.safe_shortest.found and not p.recommended.found
    assert "limit" in p.recommended.error


def test_disconnected_places_raise():
    g = three_streets()
    for n, x in (("X", 0.0), ("Y", 100.0)):  # a separate street with no link to the others
        g.add_node(n, x=x, y=1000.0, kind="junction", in_study_area=True)
    geom = LineString([(0, 1000), (100, 1000)])
    g.add_edge("X", "Y", geometry=geom, length_m=100.0, edge_id="e9", cost_factor=1.0, in_study_area=True)
    with pytest.raises(RoutingError):
        plan_routes(Router(g), Point(*A), Point(50, 1000), FLOOD, TravellerProfile(ADULT))
