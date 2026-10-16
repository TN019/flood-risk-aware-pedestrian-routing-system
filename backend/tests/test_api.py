"""The web API on a small street grid placed in Southbank, so no downloaded data is needed.

Two parallel 300 m streets 100 m apart, joined at both ends; a building "Shelter" between them with
its door 30 m north of the bottom street.
"""

import geopandas as gpd
import networkx as nx
import pytest
from fastapi.testclient import TestClient
from pyproj import Transformer
from shapely.geometry import LineString, Point, box

from floodroute import config
from floodroute.api.app import create_app
from floodroute.api.service import Scenario, Service
from floodroute.hazard import DRY, EdgeCondition, HazardSnapshot, NoHazard
from floodroute.hazard.catalog import ScenarioInfo
from floodroute.places import PlaceResolver
from floodroute.places.refuges import RefugeIndex
from floodroute.routing import Router

X0, Y0 = 320_000.0, 5_812_000.0  # MGA zone 55, Southbank
TO_WGS = Transformer.from_crs(config.METRIC_CRS, config.WGS84, always_xy=True)


def at(x: float, y: float) -> dict:
    lon, lat = TO_WGS.transform(X0 + x, Y0 + y)
    return {"lat": lat, "lon": lon}


class StaticHazard:
    def __init__(self, **depths):
        self.depths = depths

    def snapshot(self, graph, at=None):
        conditions = {e: EdgeCondition(d) for e, d in self.depths.items()}
        return HazardSnapshot("test", at, conditions, DRY)


def town_service() -> Service:
    xy = {1: (0, 0), 2: (150, 0), 3: (300, 0), 4: (0, 100), 5: (300, 100)}
    g = nx.Graph(crs=config.METRIC_CRS, study_area=box(X0 - 50, Y0 - 50, X0 + 350, Y0 + 150), buffer_m=50.0)
    for n, (x, y) in xy.items():
        g.add_node(n, x=X0 + x, y=Y0 + y, kind="junction", in_study_area=True)
    for i, (u, v) in enumerate(((1, 2), (2, 3), (1, 4), (4, 5), (5, 3))):
        geom = LineString([(X0 + xy[u][0], Y0 + xy[u][1]), (X0 + xy[v][0], Y0 + xy[v][1])])
        g.add_edge(u, v, geometry=geom, length_m=geom.length, edge_id=f"e{i}", cost_factor=1.0, in_study_area=True)
    router = Router(g)
    buildings = gpd.GeoDataFrame(
        {"name": ["Shelter"], "geometry": [box(X0 + 100, Y0 + 30, X0 + 140, Y0 + 70)]}, crs=config.METRIC_CRS
    )
    entrances = gpd.GeoDataFrame(
        {"element": ["node"], "id": [1], "entrance": ["main"], "geometry": [Point(X0 + 120, Y0 + 30)]},
        crs=config.METRIC_CRS,
    )
    resolver = PlaceResolver(buildings, entrances, router.footpaths)
    scenarios = [
        Scenario(ScenarioInfo("dry", 0, "Dry", "No water", "none"), NoHazard()),
        Scenario(ScenarioInfo("wet", 1, "Wet", "Bottom street flooded", "test"), StaticHazard(e0=0.5)),
    ]
    return Service(router, resolver, RefugeIndex(resolver), scenarios)


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(town_service, serve_client=False)) as c:
        yield c


def trip(client, scenario="wet", start=(0, -5), end=(300, -5), **traveller):
    body = {
        "start": at(*start),
        "destination": at(*end),
        "scenario_id": scenario,
        "traveller": {"height_cm": 170, "wading": "ankle", **traveller},
    }
    return client.post("/api/trip", json=body)


def test_options_list_every_choice(client):
    o = client.get("/api/options").json()
    assert [p["key"] for p in o["body_parts"]] == ["no_wading", "ankle", "lower_calf", "mid_calf"]
    assert [p["key"] for p in o["preferences"]] == ["shortest", "balanced", "avoid_water", "driest"]
    assert [lv["key"] for lv in o["flood_levels"]] == ["light", "moderate", "heavy", "extreme"]
    assert o["hard_limit_m"] == 0.30 and o["default_preference"] == "balanced"


def test_scenarios_report_their_level_and_water(client):
    dry, wet = client.get("/api/scenarios").json()
    assert dry["level"] is None and dry["typical_depth_m"] is None
    assert wet["level"]["key"] == "heavy" and wet["typical_depth_m"] == pytest.approx(0.5)
    water = client.get("/api/scenarios/wet/water").json()
    assert [f["properties"]["depth_m"] for f in water["features"]] == [0.5]
    assert client.get("/api/scenarios/dry/water").json()["features"] == []
    assert client.get("/api/scenarios/nope/water").status_code == 404


def test_area_and_network_are_geojson_in_wgs84(client):
    area = client.get("/api/area").json()
    west, south, east, north = area["bounds"]
    assert 144.9 < west < east < 145.0 and -37.9 < south < north < -37.8
    network = client.get("/api/network").json()
    assert len(network["features"]) == 5 and {f["properties"]["kind"] for f in network["features"]} == {"path"}


def test_dry_trip_takes_the_short_street(client):
    r = trip(client, scenario="dry")
    assert r.status_code == 200
    j = r.json()
    assert j["has_safe_route"] and j["origin"]["level"] == "ok"
    lengths = {o["kind"]: o["route"]["metrics"]["length_m"] for o in j["routes"]["options"]}
    assert lengths["recommended"] == pytest.approx(310, abs=1)  # 300 m + two 5 m access legs
    assert len(set(lengths.values())) == 1
    assert j["downgrade"] is None and j["refuge"] is None and j["emergency"] is None


def test_flooded_street_is_avoided_and_shown_on_the_shortest_route(client):
    j = trip(client).json()
    options = {o["kind"]: o for o in j["routes"]["options"]}
    assert options["shortest"]["route"]["metrics"]["segments_over_limit"] >= 1
    assert options["shortest"]["route"]["metrics"]["max_depth_m"] == pytest.approx(0.5)
    assert options["recommended"]["route"]["metrics"]["length_m"] == pytest.approx(510, abs=1)
    assert options["recommended"]["route"]["metrics"]["max_depth_m"] == 0
    assert j["traveller"]["depth_limit_m"] == pytest.approx(0.0663)


def test_standing_in_deep_water_offers_help_and_the_shelter(client):
    j = trip(client, start=(75, -2)).json()
    assert j["origin"]["level"] == "very_deep" and j["origin"]["depth_m"] == pytest.approx(0.5)
    assert j["emergency"]["advice"] == "recommended"
    assert j["emergency"]["sos"]["depth_m"] == pytest.approx(0.5)
    assert j["refuge"]["name"] == "Shelter" and not j["refuge"]["within_limit"]


def test_requests_outside_southbank_or_invalid_are_refused(client):
    r = trip(client, start=(-500, -500))
    assert r.status_code == 422 and "inside Southbank" in r.json()["detail"]
    assert trip(client, scenario="nope").status_code == 422
    assert trip(client, wading="knee").status_code == 422
    assert trip(client, height_cm=20).status_code == 422


def test_traveller_explains_the_preference(client):
    j = client.post("/api/traveller", json={"height_cm": 170, "wading": "no_wading"}).json()
    assert j["depth_limit_m"] == pytest.approx(0.02) and "no effect" in j["explanation"]
    j = client.post("/api/traveller", json={"height_cm": 170, "wading": "mid_calf", "preference": "driest"}).json()
    assert j["alpha"] == 15 and "further" in j["explanation"]
