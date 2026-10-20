"""The API's languages: complete catalogues, the same wording as the engine in English, the
language a request asks for, and translated responses."""

import re
from string import Formatter

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Point

from floodroute import config
from floodroute.api import i18n
from floodroute.api.app import create_app
from floodroute.hazard.catalog import list_scenarios
from floodroute.places.refuges import UNNAMED
from floodroute.places.resolver import BUILDING_EDGE, CHOSEN_POINT, ENTRANCE, MAIN_ENTRANCE, AccessPoint
from floodroute.risk import BodyPart, MobilityAid, TravellerProfile, describe_depth
from floodroute.risk.levels import FloodLevel
from floodroute.risk.preference import RoutePreference, explain
from floodroute.risk.profile import LANDMARKS
from floodroute.routing.planning import NO_STEP_FREE_ROUTE
from test_api import at, town_service

OTHERS = [lang for lang in i18n.LANGUAGES if lang != i18n.DEFAULT_LANGUAGE]
ENGLISH = i18n.catalogue("en")
SCENARIOS = list_scenarios(config.SCENARIO_DIR)


def placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in Formatter().parse(template) if name is not None}


def numbers(template: str) -> set[str]:
    """Every number in a text, e.g. "0.59", "1:14", "132", "500"; Devanagari or other digits count
    as different numbers, so every language must write them as in English."""
    return set(re.findall(r"\d+(?:[.,:]\d+)*", template))


def same_numbers(translation: str, english: str) -> bool:
    """The translation has every number of the English and no other; the "1" of "1-in-100-year" may
    be left out, as in "100-year"."""
    required = numbers(re.sub(r"\b1-in-(?=\d)", "", english))
    return required <= numbers(translation) <= numbers(english)


def scenario_english() -> dict[str, str]:
    """The scenarios' text in English, by the key each language gives it."""
    words = {}
    for s in SCENARIOS:
        words[f"scenario.{s.id}.title"] = s.title
        words[f"scenario.{s.id}.description"] = s.description
        for note in s.params.get("sources", []):
            words[f"scenario.source.{note}"] = note
    return words


def scenario_keys() -> set[str]:
    return set(scenario_english())


@pytest.mark.parametrize("lang", OTHERS)
def test_every_language_has_every_sentence(lang):
    words = i18n.catalogue(lang)
    assert set(words) == set(ENGLISH) | scenario_keys()
    assert all(isinstance(v, str) and v.strip() for v in words.values())


@pytest.mark.parametrize("lang", OTHERS)
def test_translations_keep_placeholders_and_numbers(lang):
    words = i18n.catalogue(lang)
    english = {**ENGLISH, **scenario_english()}
    for key, source in english.items():
        assert placeholders(words[key]) == placeholders(source), key
        assert same_numbers(words[key], source), key


def test_english_catalogue_says_what_the_engine_says():
    t = lambda key, **v: i18n.text("en", key, **v)  # noqa: E731
    for part in BodyPart:
        assert t(f"body_part.{part.name.lower()}") == part.label
    height = 1.7
    for fraction, name in LANDMARKS:
        depth = fraction * height
        assert (
            i18n.depth_label("en", depth, height)
            == describe_depth(depth, height)
            == t(f"depth.{name.replace(' ', '_')}")
        )
    for depth in (None, 0.01, 2.0):
        assert i18n.depth_label("en", depth, height) == describe_depth(depth, height)
    for aid in MobilityAid:
        assert t(f"mobility_aid.{aid.name.lower()}") == aid.label
        for level in aid.levels:
            assert t(f"aid_level.{level.key}") == level.label
    for preference in RoutePreference:
        assert t(f"preference.{preference.name.lower()}") == preference.label
        assert t(f"preference.{preference.name.lower()}.summary") == preference.summary
    for level in FloodLevel:
        assert t(f"flood_level.{level.name.lower()}") == level.label
        assert t(f"flood_level.{level.name.lower()}.range") == level.body_range
    for profile in (
        TravellerProfile(1.7, BodyPart.KNEE),
        TravellerProfile(1.2, BodyPart.ANKLE),
        TravellerProfile(1.7, BodyPart.NO_WADING),
        TravellerProfile(1.7, mobility_aid=MobilityAid.MANUAL_WHEELCHAIR, aid_level=2),
    ):
        for alpha in (0.5, 2.0, 15.0):
            assert i18n.explanation("en", alpha, profile) == explain(alpha, profile)
    for kind in (MAIN_ENTRANCE, ENTRANCE, BUILDING_EDGE, CHOSEN_POINT):
        for name in (None, "Riverside"):
            access = AccessPoint(Point(0, 0), kind, name)
            assert i18n.access_label("en", access) == access.label
    assert t("place.building") == UNNAMED
    assert t("route_error.no_step_free_route") == NO_STEP_FREE_ROUTE


def test_the_language_asked_for():
    assert i18n.negotiate("es", "ko") == "es"
    assert i18n.negotiate("fr", "ko,en;q=0.8") == "ko"
    assert i18n.negotiate(None, "fr-FR, hi;q=0.5, es;q=0.7") == "es"
    assert i18n.negotiate(None, "zh-TW,zh;q=0.9") == "zh-Hans"
    assert i18n.negotiate("zh-Hans-CN") == "zh-Hans"
    assert i18n.negotiate(None, "ko;q=0, de") == "en"
    assert i18n.negotiate(None, "en-AU,es;q=0.9") == "en"
    assert i18n.negotiate(None, "q=;;,,") == "en"
    assert i18n.negotiate() == "en"


def test_scenarios_are_described_in_every_language():
    for lang in OTHERS:
        for s in SCENARIOS:
            title, description = i18n.scenario_text(lang, s)
            assert (title, description) != (s.title, s.description)
            sources = i18n.scenario_sources(lang, s)
            assert len(sources) == len(s.params.get("sources", []))
            assert not set(sources) & set(s.params.get("sources", [])), (lang, s.id)
    for s in SCENARIOS:
        assert i18n.scenario_text("en", s) == (s.title, s.description)
        assert i18n.scenario_sources("en", s) == s.params.get("sources", [])


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(town_service, serve_client=False)) as c:
        yield c


def test_options_come_in_the_language_asked_for(client):
    english = client.get("/api/options").json()
    for lang in OTHERS:
        response = client.get(f"/api/options?lang={lang}")
        assert response.headers["content-language"] == lang
        words = response.json()
        assert [p["key"] for p in words["body_parts"]] == [p["key"] for p in english["body_parts"]]
        assert words["body_parts"][1]["label"] == i18n.text(lang, "body_part.ankle")
        assert words["landmarks"][3]["label"] == i18n.text(lang, "depth.knee")
        assert words["mobility_aids"][0]["label"] == i18n.text(lang, "mobility_aid.manual_wheelchair")
        assert words["preferences"][1]["summary"] == i18n.text(lang, "preference.balanced.summary")
        assert words["flood_levels"][0]["body_range"] == i18n.text(lang, "flood_level.light.range")
        # Numbers stay as they are.
        assert [p["fraction"] for p in words["body_parts"]] == [p["fraction"] for p in english["body_parts"]]
    accept = client.get("/api/options", headers={"Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"})
    assert accept.headers["content-language"] == "ko"
    assert accept.json()["preferences"][0]["label"] == i18n.text("ko", "preference.shortest")
    assert client.get("/api/options?lang=fr").headers["content-language"] == "en"


def test_traveller_explanation_in_the_language_asked_for(client):
    body = {"height_cm": 170, "wading": "knee", "preference": "balanced"}
    words = client.post("/api/traveller?lang=hi", json=body).json()
    assert words["limit_label"] == i18n.text("hi", "depth.knee")
    assert words["explanation"] == i18n.explanation("hi", 2.0, TravellerProfile(1.7, BodyPart.KNEE))
    assert "50" in words["explanation"]


def test_trip_text_in_the_language_asked_for(client):
    body = {
        "start": at(0, 0),
        "destination": at(300, 0),
        "scenario_id": "wet",
        "traveller": {"height_cm": 170, "wading": "ankle"},
    }
    english = client.post("/api/trip", json=body).json()
    english_shortest = next(o for o in english["routes"]["options"] if o["kind"] == "shortest")["route"]["metrics"]
    trip = client.post("/api/trip?lang=zh-Hans", json=body).json()
    names = {o["kind"]: o["name"] for o in trip["routes"]["options"]}
    assert names == {kind: i18n.text("zh-Hans", f"route.{kind}") for kind in names}
    shortest = next(o for o in trip["routes"]["options"] if o["kind"] == "shortest")["route"]["metrics"]
    assert shortest["max_depth_label"] == i18n.depth_label("zh-Hans", 0.5, 1.7)
    assert trip["traveller"]["limit_label"] == i18n.text("zh-Hans", "depth.ankle")
    # The same plan, worded differently.
    assert trip["has_safe_route"] == english["has_safe_route"]
    assert shortest["length_m"] == english_shortest["length_m"]


def test_errors_in_the_language_asked_for(client):
    body = {"start": {"lat": -37.9, "lon": 145.1}, "destination": at(300, 0), "scenario_id": "dry"}
    english = client.post("/api/trip", json=body)
    assert english.status_code == 422
    assert english.json()["detail"] == i18n.text("en", "error.start_outside_area")
    korean = client.post("/api/trip?lang=ko", json=body)
    assert korean.status_code == 422
    assert korean.json()["detail"] == i18n.text("ko", "error.start_outside_area")
    unknown = client.post("/api/trip", json={**body, "scenario_id": "nope"}, headers={"Accept-Language": "es"})
    assert unknown.json()["detail"] == i18n.text("es", "error.unknown_scenario", id="'nope'")
    water = client.get("/api/scenarios/nope/water?lang=hi")
    assert water.status_code == 404
    assert water.json()["detail"] == i18n.text("hi", "error.unknown_scenario", id="'nope'")
    level = client.post("/api/traveller?lang=es", json={"mobility_aid": "powered_wheelchair", "aid_level": 3})
    assert level.status_code == 422
    assert level.json()["detail"] == i18n.text("es", "error.no_aid_level", level=3)
