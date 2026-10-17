import geopandas as gpd
import networkx as nx
import pytest
from shapely.geometry import LineString, Point, box

from floodroute import config
from floodroute.hazard import DRY, EdgeCondition, HazardSnapshot
from floodroute.places import PlaceResolver
from floodroute.places.refuges import RefugeIndex
from floodroute.risk import HARD_LIMIT_M, BodyPart, MobilityAid, TravellerProfile
from floodroute.risk.alerts import AlertLevel, alert_level
from floodroute.routing import Router
from floodroute.trip import ONLY_OPTION, plan_trip

ADULT = 1.70

# A ladder: low street y=0 (e0: x 0..150, e1: x 150..300), connectors at x=0 (e2) and x=300 (e4),
# high street y=100 (e3). Building "North" sits above the high street with a door on its south
# wall; building "South" sits below the low street with a door on its north wall.
NORTH = box(20, 110, 60, 140)
SOUTH = box(200, -40, 240, -10)


def ladder():
    g = nx.Graph(crs=config.METRIC_CRS)
    xy = {1: (0, 0), 2: (150, 0), 3: (300, 0), 4: (0, 100), 5: (300, 100)}
    for n, (x, y) in xy.items():
        g.add_node(n, x=x, y=y, kind="junction", in_study_area=True)
    for i, (u, v) in enumerate(((1, 2), (2, 3), (1, 4), (4, 5), (5, 3))):
        geom = LineString([xy[u], xy[v]])
        g.add_edge(u, v, geometry=geom, length_m=geom.length, edge_id=f"e{i}", cost_factor=1.0, in_study_area=True)
    return g


def world(buildings=((NORTH, "North", (40, 110)), (SOUTH, "South", (220, -10)))):
    router = Router(ladder())
    b = gpd.GeoDataFrame(
        {"name": [n for _, n, _ in buildings], "geometry": [g for g, _, _ in buildings]},
        geometry="geometry",
        crs=config.METRIC_CRS,
    )
    doors = [d for _, _, d in buildings] or [(9e5, 9e5)]  # the resolver needs at least one entrance
    e = gpd.GeoDataFrame(
        {"element": "node", "id": range(len(doors)), "entrance": "main", "geometry": [Point(*d) for d in doors]},
        geometry="geometry",
        crs=config.METRIC_CRS,
    )
    resolver = PlaceResolver(b, e, router.footpaths)
    return router, resolver, RefugeIndex(resolver)


def snapshot(**depths):
    return HazardSnapshot("t", conditions={k: EdgeCondition(v) for k, v in depths.items()}, default=DRY)


def trip(snap, profile, origin=(75, 0), destination=(300, 50), buildings=None):
    router, resolver, refuges = world() if buildings is None else world(buildings)
    o = resolver.resolve(Point(*origin), "origin", role="origin")
    d = resolver.resolve(Point(*destination), "destination")
    return plan_trip(router, refuges, o, d, snap, profile)


# ------------------------------------------------------------------ alert levels


@pytest.mark.parametrize(
    "depth, level",
    [
        (0.05, AlertLevel.OK),
        (0.10, AlertLevel.OVER_LIMIT),
        (0.45, AlertLevel.OVER_LIMIT),  # under the knee and under 50 cm
        (0.50, AlertLevel.VERY_DEEP),
        (0.90, AlertLevel.CRITICAL),
        (None, AlertLevel.CRITICAL),
    ],
)
def test_alert_levels_for_an_adult(depth, level):
    assert alert_level(depth, TravellerProfile(ADULT, BodyPart.ANKLE)) == level  # limit 6.6 cm, knee 48 cm


def test_alert_levels_are_stricter_for_a_child():
    child = TravellerProfile(1.20, BodyPart.ANKLE)  # knee 34 cm, half height 60 cm
    assert alert_level(0.35, child) == AlertLevel.VERY_DEEP
    assert alert_level(0.35, TravellerProfile(ADULT, BodyPart.ANKLE)) == AlertLevel.OVER_LIMIT
    assert alert_level(0.65, child) == AlertLevel.CRITICAL


def test_deep_applies_between_50_cm_and_the_knee_of_a_tall_person():
    tall = TravellerProfile(1.90, BodyPart.ANKLE)  # knee 54 cm
    assert alert_level(0.50, tall) == AlertLevel.OVER_LIMIT
    assert alert_level(0.52, tall) == AlertLevel.DEEP
    assert alert_level(0.55, tall) == AlertLevel.VERY_DEEP


def test_emergency_advice_by_level():
    assert AlertLevel.OVER_LIMIT.emergency_advice is None
    assert AlertLevel.DEEP.emergency_advice == "available"
    assert AlertLevel.VERY_DEEP.emergency_advice == "recommended"
    assert AlertLevel.CRITICAL.emergency_advice == "strongly recommended"


# ------------------------------------------------------------------ trips


def test_dry_trip_needs_no_alternatives():
    plan = trip(snapshot(), TravellerProfile(ADULT, BodyPart.ANKLE))
    assert plan.has_safe_route and plan.origin.level == AlertLevel.OK
    assert plan.downgrade is None and plan.refuge is None and plan.emergency is None


def test_downgrade_finds_the_smallest_body_part_that_works():
    # Both ways to the corner at (300, 0) are wet: low street e1 10 cm, connector e4 15 cm. Ankle
    # (6.6 cm) cannot pass; lower calf (20.6 cm) can, and the least water to face is 10 cm.
    plan = trip(snapshot(e1=0.10, e4=0.15), TravellerProfile(ADULT, BodyPart.ANKLE), destination=(300, 0))
    assert not plan.has_safe_route
    assert plan.downgrade.body_part is BodyPart.LOWER_CALF
    assert plan.downgrade.required_depth_m == pytest.approx(0.10)
    assert plan.downgrade.option.metrics.max_depth_m == pytest.approx(0.10)


def test_no_downgrade_for_wheelchair_users_or_beyond_the_hard_limit():
    assert trip(snapshot(e1=0.10, e4=0.15), TravellerProfile(ADULT, uses_wheelchair=True)).downgrade is None
    assert trip(snapshot(e1=0.55, e4=0.55), TravellerProfile(ADULT, BodyPart.ANKLE)).downgrade is None
    knee = trip(snapshot(e1=0.40, e4=0.40), TravellerProfile(ADULT, BodyPart.ANKLE)).downgrade
    assert knee.body_part == BodyPart.KNEE and knee.required_depth_m == pytest.approx(0.40)


def test_refuge_from_dry_ground_stays_within_the_limit():
    # The destination is cut off by deep water; the North building is reachable dry via e2 and e3.
    plan = trip(snapshot(e1=0.4, e4=0.4), TravellerProfile(ADULT, BodyPart.ANKLE))
    assert plan.refuge.refuge.name == "North" and plan.refuge.within_limit
    assert plan.emergency is None


def test_refuge_from_deep_water_is_the_safest_way_out():
    # A 190 cm traveller (knee 54 cm) standing in 52 cm on e0. South is closer but its door is
    # reached through 60 cm on e1; North is reached through the 52 cm they are already in.
    plan = trip(snapshot(e0=0.52, e1=0.60, e4=0.60), TravellerProfile(1.90, BodyPart.ANKLE))
    assert plan.origin.level == AlertLevel.DEEP
    assert plan.refuge.refuge.name == "North" and not plan.refuge.within_limit
    assert plan.refuge.metrics.max_depth_m == pytest.approx(0.52)
    assert plan.emergency.advice == "available" and plan.emergency.sos.depth_m == pytest.approx(0.52)
    assert plan.downgrade is None  # get out of the water first


def test_critical_depth_strongly_recommends_help():
    plan = trip(snapshot(e0=0.90), TravellerProfile(ADULT, BodyPart.MID_CALF))
    assert plan.origin.level == AlertLevel.CRITICAL
    assert plan.emergency.advice == "strongly recommended"
    assert plan.refuge is not None  # still shown, for when waiting is not possible


def test_emergency_is_the_only_option_when_nothing_is_reachable():
    plan = trip(snapshot(e0=0.2, e1=0.4, e4=0.4, e2=0.4), TravellerProfile(ADULT, BodyPart.ANKLE), buildings=())
    assert plan.refuge is None and plan.emergency.advice == ONLY_OPTION


def test_starting_inside_a_building_counts_as_sheltered():
    plan = trip(snapshot(e1=0.4, e4=0.4), TravellerProfile(ADULT, BodyPart.ANKLE), origin=(40, 125))
    assert plan.origin.sheltered and plan.origin.level == AlertLevel.OK
    assert plan.refuge is None and plan.emergency is None


def test_a_corner_beside_a_flooded_street_is_not_deep_water():
    # The origin sits on node 1, where dry e2 meets flooded e0: the traveller stands on the dry one.
    plan = trip(snapshot(e0=0.40), TravellerProfile(ADULT, BodyPart.ANKLE), origin=(0, 0))
    assert plan.origin.level == AlertLevel.OK
    assert plan.has_safe_route


@pytest.mark.skipif(
    not (config.PROCESSED_NETWORK_PATH.exists() and config.PROCESSED_PLACES_PATH.exists()),
    reason="processed network not built",
)
def test_plans_on_the_southbank_network_are_consistent():
    import random

    from floodroute.hazard.catalog import list_scenarios, load_hazard
    from floodroute.network import load_graph

    g = load_graph(config.PROCESSED_NETWORK_PATH)
    router = Router(g)
    places = config.PROCESSED_PLACES_PATH
    resolver = PlaceResolver(
        gpd.read_file(places, layer="buildings"), gpd.read_file(places, layer="entrances"), router.footpaths
    )
    refuges = RefugeIndex(resolver, g.graph["study_area"].buffer(g.graph["buffer_m"]))
    heavy = next(s for s in list_scenarios() if s.id == "heavy-flooding")
    snap = load_hazard(heavy).snapshot(g)
    area = g.graph["study_area"]
    minx, miny, maxx, maxy = area.bounds
    rng = random.Random(9)
    profile = TravellerProfile(ADULT, BodyPart.ANKLE)
    checked = 0
    while checked < 40:
        a, b = (Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy)) for _ in range(2))
        if not (area.contains(a) and area.contains(b)):
            continue
        o, d = resolver.resolve(a, "o", role="origin"), resolver.resolve(b, "d")
        plan = plan_trip(router, refuges, o, d, snap, profile)
        checked += 1
        if plan.has_safe_route:
            assert plan.routes.recommended.metrics.segments_over_limit == 0
        if plan.refuge is not None:
            assert plan.refuge.within_limit == (plan.refuge.metrics.segments_over_limit == 0)
        if plan.origin.level >= AlertLevel.DEEP:
            assert plan.emergency is not None and plan.downgrade is None
        if plan.downgrade is not None:
            assert plan.downgrade.depth_limit_m >= plan.downgrade.required_depth_m
            assert plan.downgrade.required_depth_m <= HARD_LIMIT_M


# ------------------------------------------------------------------ least water


def test_least_water_shows_why_no_route_fits_and_where():
    plan = trip(snapshot(e1=0.40, e4=0.40), TravellerProfile(ADULT, BodyPart.ANKLE))
    least = plan.least_water
    assert not plan.has_safe_route
    assert least.required_depth_m == pytest.approx(0.40)
    assert least.metrics.max_depth_m == pytest.approx(0.40)
    assert least.deepest_at.equals(Point(225, 0))  # middle of e1, the first 40 cm piece on the way
    assert plan.downgrade.body_part == BodyPart.KNEE  # derived from the same route


def test_least_water_is_reported_beyond_the_hard_limit_without_a_downgrade():
    plan = trip(snapshot(e1=0.55, e4=0.55), TravellerProfile(ADULT, BodyPart.MID_CALF))
    assert plan.least_water.required_depth_m == pytest.approx(0.55)
    assert plan.downgrade is None


def test_no_least_water_when_a_route_fits():
    assert trip(snapshot(), TravellerProfile(ADULT, BodyPart.ANKLE)).least_water is None


# ------------------------------------------------------------------ mobility aids


def test_mobility_aid_downgrade_is_the_next_level_of_the_same_device():
    manual = TravellerProfile(ADULT, mobility_aid=MobilityAid.MANUAL_WHEELCHAIR)
    d = trip(snapshot(e1=0.04, e4=0.04), manual).downgrade
    assert d.body_part is None and d.aid_level == 1 and d.label == "below a 4-inch castor axle"
    assert d.depth_limit_m == pytest.approx(0.05) and d.required_depth_m == pytest.approx(0.04)
    d = trip(snapshot(e1=0.07, e4=0.07), manual).downgrade
    assert d.aid_level == 2 and d.depth_limit_m == pytest.approx(0.075)


def test_no_mobility_aid_downgrade_beyond_the_device_cap():
    scooter = TravellerProfile(ADULT, mobility_aid=MobilityAid.MOBILITY_SCOOTER)
    plan = trip(snapshot(e1=0.04, e4=0.04), scooter)
    assert plan.least_water.required_depth_m == pytest.approx(0.04) and plan.downgrade is None
    powered = TravellerProfile(ADULT, mobility_aid=MobilityAid.POWERED_WHEELCHAIR)
    assert trip(snapshot(e1=0.07, e4=0.07), powered).downgrade is None
