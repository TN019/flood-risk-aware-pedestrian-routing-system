"""Generate the synthetic flood scenarios in data/scenarios/.

Five escalating levels of one illustrative storm over Southbank:

    0 normal      no standing water
    1 light       shallow kerbside ponding at crossings and a low point (≤ 5 cm)
    2 moderate    ponding on key footpaths and the riverfront (≤ 25 cm)
    3 severe      riverbank overtopped; Kings Way, City Road and Southbank Boulevard flooded (≤ 45 cm)
    4 extreme     riverine flood reaching deep into Southbank (up to ~1 m)

The zones are placed at plausible spots (riverbank, arterial roads, low points, crossings) but
are synthetic, not the output of a flood model. Corridors follow OSM ways by name and the
riverfront follows the OSM river polygon, so the scenarios line up with the network. Output is
deterministic; rerun after rebuilding the network or changing the definitions below.

Requires data/processed (scripts/build_network.py) and data/raw/osm_water (scripts/download_data.py).

Run:  uv run python scripts/make_scenarios.py
"""

from __future__ import annotations

import json
import random

import geopandas as gpd
from shapely.geometry import LineString, Point, mapping
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from floodroute import config
from floodroute.network import load_graph, to_gdfs
from floodroute.sources.com import load_study_area

SEED = 11
CROSSING_PUDDLES = 12
PUDDLE_SPACING_M = 120.0


def metric(lat: float, lon: float) -> Point:
    return gpd.GeoSeries([Point(lon, lat)], crs=config.WGS84).to_crs(config.METRIC_CRS).iloc[0]


def zone(name: str, geom: BaseGeometry, depth: float, ramp: float) -> dict:
    return {"name": name, "geometry": geom, "max_depth_m": round(depth, 3), "ramp_m": ramp}


class Places:
    """Reusable geometry anchors taken from the network and OSM layers."""

    def __init__(self):
        graph = load_graph(config.PROCESSED_NETWORK_PATH)
        self.area = load_study_area()
        self.clip = self.area.buffer(config.STUDY_AREA_BUFFER_M)
        _, self.edges = to_gdfs(graph)
        water = gpd.read_file(config.OSM_WATER_PATH).to_crs(config.METRIC_CRS)
        water = water[water.geom_type.isin(["Polygon", "MultiPolygon"])]
        self.river = unary_union(list(water[water.intersects(self.clip)].geometry))

    def road(self, name: str) -> BaseGeometry:
        """All network edges named ``name`` (sidewalks and carriageway) inside the study area."""
        named = self.edges[self.edges["name"].fillna("").str.contains(name, regex=False)]
        return unary_union(list(named[named.intersects(self.area)].geometry))

    def river_band(self, inland_m: float) -> BaseGeometry:
        return self.river.buffer(inland_m).intersection(self.clip)

    def crossing_points(self) -> list[Point]:
        """Midpoints of well-spread signalised/zebra crossings inside Southbank."""
        crossings = self.edges[self.edges["is_crossing"].fillna(False).astype(bool) & self.edges.within(self.area)]
        mids = [g.interpolate(0.5, normalized=True) for g in crossings.sort_values("edge_id").geometry]
        random.Random(SEED).shuffle(mids)
        picked: list[Point] = []
        for p in mids:
            if all(p.distance(q) >= PUDDLE_SPACING_M for q in picked):
                picked.append(p)
            if len(picked) == CROSSING_PUDDLES:
                break
        return picked


def puddles(places: Places, low: float, high: float) -> list[dict]:
    rng = random.Random(SEED)
    return [
        zone(f"Ponding at crossing {i + 1}", p.buffer(7), rng.uniform(low, high), 2)
        for i, p in enumerate(places.crossing_points())
    ]


def scenarios(places: Places) -> list[dict]:
    kings_way_footpath = LineString([metric(-37.825792, 144.959901), metric(-37.82443, 144.958439)])
    promenade_west = LineString([metric(-37.820719, 144.962122), metric(-37.820217, 144.964355)])
    city_road_low = metric(-37.824211, 144.962657)
    riverside_quay = metric(-37.821313, 144.964388)
    south_wharf_low = LineString([metric(-37.8248, 144.9500), metric(-37.8232, 144.9560)])
    return [
        {
            "id": "normal",
            "order": 0,
            "title": "Normal conditions",
            "description": "No standing water. Routes should match the plain shortest walking routes.",
            "zones": [],
        },
        {
            "id": "light-ponding",
            "order": 1,
            "title": "Light ponding",
            "description": "Shallow kerbside ponding at twelve crossings (3–5 cm) and at a City Road low point "
            "(5 cm). Passable for most adults; blocks routes for people who will not wade at all.",
            "zones": [
                *puddles(places, 0.03, 0.05),
                zone("City Road low point", city_road_low.buffer(25), 0.05, 8),
            ],
        },
        {
            "id": "moderate-flooding",
            "order": 2,
            "title": "Moderate flooding",
            "description": "Ponding on the Kings Way west footpath (20 cm), the riverfront promenade west of "
            "Southgate (25 cm), Riverside Quay (15 cm) and City Road (12 cm); crossings hold 6–9 cm.",
            "zones": [
                *puddles(places, 0.06, 0.09),
                zone("Kings Way west footpath", kings_way_footpath.buffer(10), 0.20, 6),
                zone("Riverfront promenade west of Southgate", promenade_west.buffer(18), 0.25, 10),
                zone("Riverside Quay", riverside_quay.buffer(30), 0.15, 10),
                zone("City Road low point", city_road_low.buffer(35), 0.12, 10),
            ],
        },
        {
            "id": "severe-flooding",
            "order": 3,
            "title": "Severe flooding",
            "description": "The Yarra overtops its bank along the whole riverfront (45 cm); Kings Way (30 cm), "
            "City Road (25 cm) and Southbank Boulevard (20 cm) are flooded; crossings hold 10–15 cm.",
            "zones": [
                *puddles(places, 0.10, 0.15),
                zone("Riverfront", places.river_band(35), 0.45, 20),
                zone("Kings Way", places.road("Kings Way").buffer(18), 0.30, 8),
                zone("City Road", places.road("City Road").buffer(15), 0.25, 8),
                zone("Southbank Boulevard", places.road("Southbank Boulevard").buffer(15), 0.20, 8),
            ],
        },
        {
            "id": "extreme-flooding",
            "order": 4,
            "title": "Extreme flooding",
            "description": "Riverine flooding reaches about 250 m into Southbank, around 1 m deep near the river; "
            "the low-lying west around South Wharf is under 60 cm; the main roads hold 50 cm.",
            "zones": [
                *puddles(places, 0.15, 0.25),
                zone("Riverine flood", places.river_band(250), 1.0, 150),
                zone("South Wharf low ground", south_wharf_low.buffer(120), 0.60, 60),
                zone("Kings Way", places.road("Kings Way").buffer(25), 0.50, 10),
                zone("City Road", places.road("City Road").buffer(20), 0.50, 10),
                zone("Southbank Boulevard", places.road("Southbank Boulevard").buffer(20), 0.40, 10),
            ],
        },
    ]


def to_geojson(spec: dict) -> dict:
    features = []
    for z in spec["zones"]:
        geom = gpd.GeoSeries([z["geometry"]], crs=config.METRIC_CRS).to_crs(config.WGS84).iloc[0]
        features.append(
            {
                "type": "Feature",
                "properties": {"name": z["name"], "max_depth_m": z["max_depth_m"], "ramp_m": z["ramp_m"]},
                "geometry": _round(mapping(geom.simplify(0.000003))),
            }
        )
    meta = {k: spec[k] for k in ("id", "order", "title", "description")}
    return {"type": "FeatureCollection", **meta, "features": features}


def _round(obj):
    if isinstance(obj, float):
        return round(obj, 6)
    if isinstance(obj, (list, tuple)):
        return [_round(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _round(v) for k, v in obj.items()}
    return obj


def main() -> None:
    places = Places()
    config.SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    keep = set()
    for spec in scenarios(places):
        path = config.SCENARIO_DIR / f"{spec['order']}-{spec['id']}.geojson"
        path.write_text(json.dumps(to_geojson(spec), indent=1) + "\n")
        keep.add(path)
        print(f"{path.relative_to(config.REPO_ROOT)}: {len(spec['zones'])} zones")
    for stale in set(config.SCENARIO_DIR.glob("*.geojson")) - keep:
        stale.unlink()
        print(f"removed {stale.relative_to(config.REPO_ROOT)}")


if __name__ == "__main__":
    main()
