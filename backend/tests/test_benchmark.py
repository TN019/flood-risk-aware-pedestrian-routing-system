import pytest
from shapely.geometry import Point

from floodroute import verification as town
from floodroute.benchmark import correctness, faults, ground_truth
from floodroute.benchmark.safety import TRAVELLERS, rising_flood
from floodroute.benchmark.world import World, quantile
from floodroute.risk import BodyPart, TravellerProfile
from floodroute.trip import CUT_OFF
from floodroute.verification import ADULT, END, START, adult, flood


def test_minimax_matches_brute_force():
    out = correctness.minimax_against_brute_force(graphs=25, seed=7)
    assert out["pairs"] > 0 and out["match"] == out["pairs"] and not out["mismatches"]


def test_quantile():
    assert quantile([], 0.5) is None
    assert quantile([3, 1, 2], 0.5) == 2
    assert quantile([0, 10], 0.9) == pytest.approx(9)


# ------------------------------------------------------------------ faults


def _town_trip(snapshot, profile, start=START):
    from floodroute.trip import plan_trip

    router, resolver, refuges = town.test_town()
    o = resolver.resolve(start, "start", role="origin")
    return plan_trip(router, refuges, o, resolver.resolve(END, "end"), snapshot, profile)


def test_a_fault_breaks_its_rule_only_while_applied():
    inside = Point(-25, 25)
    cut_off = flood(b12=0.60, t12=0.60)
    with faults.applied("F7"):
        assert _town_trip(cut_off, adult(BodyPart.MID_CALF), inside).emergency is None
    assert _town_trip(cut_off, adult(BodyPart.MID_CALF), inside).emergency.reason == CUT_OFF


def test_no_hard_limit_fault_lifts_the_cap():
    tall = TravellerProfile(2.0, BodyPart.KNEE)
    assert tall.depth_limit_m == pytest.approx(0.50)
    with faults.applied("F3"):
        assert tall.depth_limit_m == pytest.approx(0.57)


def test_over_limit_fault_lets_routes_through_deep_water():
    deep = flood(b12=0.10)
    assert _town_trip(deep, adult()).routes.safe_shortest.route.length_m == pytest.approx(400)
    with faults.applied("F1"):
        assert _town_trip(deep, adult()).routes.safe_shortest.route.length_m == pytest.approx(300)


# ------------------------------------------------------------------ rising flood


def test_rising_flood_reroutes_from_where_the_traveller_is():
    # Dry at first; after 100 s (130 m along the bottom street, at (130, 0) on b12) b12 and t12 rise
    # to 40 cm, over the mid-calf limit. Replanned there: no route within the limit, so the safest
    # way to Shelter: 30 m back along b12 in 40 cm (escaping), then b01, c0 and the door, dry.
    router, resolver, refuges = town.test_town()
    world = World(router.graph, router, resolver, refuges, {"dry": flood(), "rise": flood(b12=0.4, t12=0.4)}, {})
    world.titles = {"dry": "dry", "rise": "rise"}
    trip = (resolver.resolve(START, "start", role="origin"), resolver.resolve(END, "end"))
    out = rising_flood(world, [trip], "adult, mid calf", (("dry", 0.0), ("rise", 100.0)))
    assert TRAVELLERS["adult, mid calf"].height_m == ADULT
    assert out["violations_m"] == 0
    assert out["reroutes"] == 1 and out["caught_by_rising_water"] == 1
    assert out["escape_over_limit_m"] == pytest.approx(30.0)
    assert out["outcomes"] == {"at a shelter": 1}


# ------------------------------------------------------------------ ground truth


def _row(kind="path", category="footpath", **kw):
    row = dict.fromkeys(ground_truth.MODEL_COLUMNS + ground_truth.FIELD_COLUMNS, "")
    row.update(kind=kind, category=category, model_steps="no", model_step_free="yes")
    row.update(kw)
    return row


def test_path_categories():
    assert ground_truth.path_category({"is_steps": True, "is_crossing": True}) == "steps"
    assert ground_truth.path_category({"is_crossing": True}) == "crossing"
    assert ground_truth.path_category({"is_carriageway": True}) == "beside carriageway"
    assert ground_truth.path_category({"highway": "footway"}) == "footpath"
    assert ground_truth.path_category({"highway": "service"}) == "street"


def test_compare_counts_false_accessible_items():
    rows = [
        _row(field_found="yes", field_passable="yes", field_steps="no"),  # agrees
        _row(field_found="yes", field_passable="yes", field_steps="yes"),  # steps the model missed
        _row(category="crossing", field_found="yes", field_passable="yes", field_steps="no", field_kerb_ramp="no"),
        _row(field_found="no"),  # not there at all
        _row(category="steps", model_steps="yes", model_step_free="no", field_found="yes", field_steps="yes"),
        _row(),  # not inspected
        _row(
            kind="entrance",
            category="building entrance",
            model_steps="",
            model_step_free="",
            field_found="yes",
            field_open_to_public="no",
            field_entrance_step_free="yes",
        ),
    ]
    out = ground_truth.compare(rows)
    assert out["inspected"] == 6
    p = out["paths"]
    assert p["inspected"] == 5
    assert p["false_accessible"] == {"count": 1, "of": 5, "rate": pytest.approx(0.2)}
    assert p["false_step_free"]["count"] == 3 and p["false_step_free"]["of"] == 4  # steps, no kerb ramp, missing
    assert p["steps_missed"] == {"count": 1, "of": 3, "rate": pytest.approx(1 / 3)}
    assert out["entrances"]["not_usable"] == {"count": 1, "of": 1, "rate": 1.0}
    assert out["entrances"]["not_step_free"]["count"] == 0
