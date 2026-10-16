import json
import random

import networkx as nx
import pytest
import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import LineString, Point, box, mapping

from floodroute import config
from floodroute.hazard import DRY, UNKNOWN, EdgeCondition, HazardSnapshot, NoHazard
from floodroute.hazard.scenarios import FloodScenario, FloodZone, ScenarioHazard, load_scenario
from floodroute.risk import (BodyPart, DepthRelativeRisk, TravellerProfile, describe_depth, risk_cost,
                             walking_cost)
from floodroute.risk.metrics import route_metrics
from floodroute.routing import Router, RoutingError

ADULT = 1.70


def ladder():
    """Two parallel 300 m streets joined at both ends: a short 'low' street (y=0) and a longer
    'high' street (y=100) via 100 m connectors. Origin (0,0), destination (300,0)."""
    g = nx.Graph(crs=config.METRIC_CRS)
    xy = {1: (0, 0), 2: (150, 0), 3: (300, 0), 4: (0, 100), 5: (300, 100)}
    for n, (x, y) in xy.items():
        g.add_node(n, x=x, y=y, kind="junction", in_study_area=True)
    for i, (u, v) in enumerate(((1, 2), (2, 3), (1, 4), (4, 5), (5, 3))):
        geom = LineString([xy[u], xy[v]])
        g.add_edge(u, v, geometry=geom, length_m=geom.length, edge_id=f"e{i}", cost_factor=1.0, in_study_area=True)
    return g


def flooded(depth, flooded_length=None):
    """Water on the low street's first half (e0, 150 m long)."""
    return HazardSnapshot("test", conditions={"e0": EdgeCondition(depth, flooded_length_m=flooded_length)},
                          default=DRY)


# ------------------------------------------------------------------ profile

@pytest.mark.parametrize("part, expected_cm", [(BodyPart.NO_WADING, 2.0), (BodyPart.ANKLE, 6.63),
                                               (BodyPart.LOWER_CALF, 20.57), (BodyPart.MID_CALF, 27.54)])
def test_body_part_limits_scale_with_height(part, expected_cm):
    assert TravellerProfile(ADULT, part).depth_limit_m * 100 == pytest.approx(expected_cm, abs=0.01)


def test_hard_limit_and_wheelchair():
    assert TravellerProfile(2.2, BodyPart.MID_CALF).depth_limit_m == pytest.approx(0.30)  # 35.6 cm capped
    assert TravellerProfile(ADULT, BodyPart.MID_CALF, uses_wheelchair=True).depth_limit_m == pytest.approx(0.02)
    assert TravellerProfile(1.2, BodyPart.LOWER_CALF).depth_limit_m < TravellerProfile(ADULT, BodyPart.LOWER_CALF).depth_limit_m
    with pytest.raises(ValueError):
        TravellerProfile(3.0)


def test_describe_depth():
    assert describe_depth(0.01, ADULT) == "dry"
    assert describe_depth(0.05, ADULT) == "up to the ankle"
    assert describe_depth(0.30, ADULT) == "up to the knee"
    assert describe_depth(0.30, 1.0) == "up to the mid thigh"  # same water, shorter person
    assert describe_depth(None, ADULT) == "unknown depth"


# ------------------------------------------------------------------ risk model

def test_depth_relative_risk():
    model, prof = DepthRelativeRisk(), TravellerProfile(ADULT, BodyPart.LOWER_CALF)  # limit 20.57 cm
    assert model.edge_risk(DRY, prof) == 0
    assert model.edge_risk(EdgeCondition(0.02), prof) == 0
    assert model.edge_risk(EdgeCondition(0.10), prof) == pytest.approx(0.10 / 0.2057, rel=1e-3)
    assert model.edge_risk(EdgeCondition(0.21), prof) is None
    assert model.edge_risk(UNKNOWN, prof) is None
    assert DepthRelativeRisk(unknown_risk=1.0).edge_risk(UNKNOWN, prof) == 1.0


def test_risk_cost_formula():
    prof = TravellerProfile(ADULT, BodyPart.MID_CALF)
    data = {"edge_id": "e0", "length_m": 150.0, "cost_factor": 1.0}
    r = 0.1 / prof.depth_limit_m
    assert risk_cost(flooded(0.1), prof, alpha=2)(1, 2, data) == pytest.approx(150 * (1 + 2 * r))
    assert risk_cost(flooded(0.1, flooded_length=30), prof, alpha=2)(1, 2, data) == pytest.approx(150 + 30 * 2 * r)
    assert risk_cost(flooded(0.1), prof, alpha=0)(1, 2, data) == pytest.approx(150)
    assert risk_cost(flooded(0.5), prof)(1, 2, data) is None
    with pytest.raises(ValueError):
        risk_cost(flooded(0.1), prof, alpha=-1)


def test_no_flood_risk_cost_equals_walking_cost_exactly():
    cost = risk_cost(NoHazard().snapshot(ladder()), TravellerProfile(ADULT, BodyPart.ANKLE), alpha=5)
    rng = random.Random(0)
    for _ in range(200):
        data = {"edge_id": "x", "length_m": rng.uniform(0, 500), "cost_factor": rng.choice([1.0, 3.0])}
        assert cost(0, 1, data) == walking_cost(0, 1, data)


# ------------------------------------------------------------------ routing (tests B, C, D, E)

def test_shallow_water_is_crossed_when_the_detour_costs_more():
    router, prof = Router(ladder()), TravellerProfile(ADULT, BodyPart.MID_CALF)
    route = router.route(Point(0, 0), Point(300, 0), risk_cost(flooded(0.05), prof, alpha=2))
    assert route.length_m == pytest.approx(300)  # 150 × (1 + 2 × 0.18) < 200 m detour


def test_lower_risk_detour_when_risk_outweighs_distance():
    router, prof = Router(ladder()), TravellerProfile(ADULT, BodyPart.MID_CALF)
    route = router.route(Point(0, 0), Point(300, 0), risk_cost(flooded(0.25), prof, alpha=2))
    assert route.length_m == pytest.approx(500)  # 150 × (1 + 2 × 0.91) > 350 via the high street


def test_unsafe_edge_is_never_used_whatever_alpha():
    router, prof = Router(ladder()), TravellerProfile(ADULT, BodyPart.ANKLE)  # limit 6.6 cm
    route = router.route(Point(0, 0), Point(300, 0), risk_cost(flooded(0.10), prof, alpha=0))
    assert route.length_m == pytest.approx(500)


def test_profiles_get_different_routes_in_the_same_flood():
    router, snap = Router(ladder()), flooded(0.10)
    adult = router.route(Point(0, 0), Point(300, 0), risk_cost(snap, TravellerProfile(ADULT, BodyPart.MID_CALF), alpha=1))
    chair = router.route(Point(0, 0), Point(300, 0),
                         risk_cost(snap, TravellerProfile(ADULT, BodyPart.MID_CALF, uses_wheelchair=True), alpha=1))
    assert adult.length_m == pytest.approx(300) and chair.length_m == pytest.approx(500)


def test_no_feasible_route_is_reported_not_forced():
    g = ladder()
    snap = HazardSnapshot("test", conditions={"e0": EdgeCondition(0.4), "e2": EdgeCondition(0.4)}, default=DRY)
    with pytest.raises(RoutingError):
        Router(g).route(Point(0, 0), Point(300, 0), risk_cost(snap, TravellerProfile(ADULT, BodyPart.MID_CALF)))


def test_conditions_follow_edges_split_at_the_route_ends():
    # Start in the middle of the flooded street: the split pieces keep e0's depth, so an ankle-deep
    # limit blocks walking along it and also blocks leaving that way.
    router, prof = Router(ladder()), TravellerProfile(ADULT, BodyPart.ANKLE)
    with pytest.raises(RoutingError):
        router.route(Point(75, 1), Point(300, 0), risk_cost(flooded(0.10), prof))


def test_metrics_report_depth_against_the_body():
    router, prof = Router(ladder()), TravellerProfile(ADULT, BodyPart.MID_CALF)
    snap = flooded(0.10, flooded_length=60)
    route = router.route(Point(0, 0), Point(300, 0), risk_cost(snap, prof, alpha=1))
    m = route_metrics(route, snap, prof, reference_length_m=300)
    assert m.max_depth_m == pytest.approx(0.10) and m.max_depth_label == "up to the lower calf"
    assert m.wading_length_m == pytest.approx(60) and m.depth_weighted_wading_m2 == pytest.approx(6)
    assert m.segments_over_limit == 0 and m.detour_ratio == pytest.approx(0)
    plain = router.route(Point(0, 0), Point(300, 0))
    strict = TravellerProfile(ADULT, BodyPart.ANKLE)
    assert route_metrics(plain, snap, strict).segments_over_limit >= 1


# ------------------------------------------------------------------ scenarios

def square_zone(depth=0.3, ramp=10):
    return FloodZone("pond", box(100, -20, 200, 20), depth, ramp)


def test_zone_depth_ramps_up_from_the_edge():
    zone = square_zone()
    assert zone.depth_at(Point(100, 0)) == 0
    assert zone.depth_at(Point(105, 0)) == pytest.approx(0.15)
    assert zone.depth_at(Point(150, 0)) == pytest.approx(0.3)
    assert zone.depth_at(Point(50, 0)) == 0


def test_scenario_conditions_use_deepest_point_and_wet_length():
    g = ladder()
    snap = ScenarioHazard(FloodScenario("t", "t", "", (square_zone(),))).snapshot(g)
    c0, c1 = snap.condition("e0"), snap.condition("e1")  # pond spans x 100..200 on the low street
    assert c0.depth_m == pytest.approx(0.3, abs=0.01) and c1.depth_m == pytest.approx(0.3, abs=0.01)
    assert c0.flooded_length_m + c1.flooded_length_m == pytest.approx(100 - 2 * 0.67, abs=2)  # minus the 2 cm rim
    assert snap.condition("e3") == DRY


def test_load_scenario_from_geojson(tmp_path):
    to_wgs = Transformer.from_crs(config.METRIC_CRS, config.WGS84, always_xy=True)
    poly = shapely.transform(box(320000, 5811000, 320050, 5811050),
                             lambda xy: np.column_stack(to_wgs.transform(xy[:, 0], xy[:, 1])))
    doc = {"type": "FeatureCollection", "id": "x", "title": "X", "description": "d",
           "features": [{"type": "Feature", "properties": {"name": "z", "max_depth_m": 0.2, "ramp_m": 5},
                         "geometry": mapping(poly)}]}
    path = tmp_path / "x.geojson"
    path.write_text(json.dumps(doc))
    scenario = load_scenario(path)
    assert scenario.id == "x" and scenario.zones[0].polygon.area == pytest.approx(2500, rel=1e-3)


def test_bundled_scenarios_load():
    from floodroute.hazard.scenarios import list_scenarios

    paths = list_scenarios()
    assert paths, "no scenario files in data/scenarios"
    for p in paths:
        s = load_scenario(p)
        assert s.zones and all(0 < z.max_depth_m < 2 for z in s.zones)


@pytest.mark.skipif(not config.PROCESSED_NETWORK_PATH.exists(), reason="processed network not built")
def test_no_flood_gives_identical_routes_on_the_southbank_network():
    from floodroute.network import load_graph

    g = load_graph(config.PROCESSED_NETWORK_PATH)
    router = Router(g)
    dry = risk_cost(NoHazard().snapshot(g), TravellerProfile(ADULT, BodyPart.NO_WADING), alpha=2)
    area = g.graph["study_area"]
    minx, miny, maxx, maxy = area.bounds
    rng = random.Random(3)
    checked = 0
    while checked < 100:
        a, b = (Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy)) for _ in range(2))
        if not (area.contains(a) and area.contains(b)):
            continue
        try:
            plain = router.route(a, b)
        except RoutingError:
            continue
        risky = router.route(a, b, dry)
        assert risky.length_m == plain.length_m and risky.geometry.equals(plain.geometry)
        checked += 1
