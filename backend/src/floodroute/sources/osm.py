"""OpenStreetMap data (ODbL) via osmnx and the Overpass API: walking network, buildings,
entrances, water and bridges for the study area."""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from floodroute import config
from floodroute.config import SOUTHBANK_BBOX, BBox

OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api",
    "https://overpass.private.coffee/api",
    "https://maps.mail.ru/osm/tools/overpass/api",
)

# Extra OSM tags kept on ways/nodes: needed to drop indoor corridors and to find carriageways
# that duplicate separately mapped sidewalks, and useful for accessibility (steps, incline, kerbs).
OSM_EXTRA_WAY_TAGS = (
    "footway", "sidewalk", "sidewalk:both", "sidewalk:left", "sidewalk:right", "foot",
    "indoor", "level", "layer", "covered", "surface", "incline", "wheelchair", "crossing",
)
OSM_EXTRA_NODE_TAGS = ("crossing", "entrance", "kerb", "wheelchair", "barrier")
BUILDING_TAGS = ("name", "building", "addr:housenumber", "addr:street", "level", "layer")
ENTRANCE_TAGS = ("name", "entrance", "door", "access", "level", "indoor", "layer", "wheelchair", "ref")


def _osmnx():
    import osmnx as ox

    ox.settings.use_cache = True
    ox.settings.cache_folder = str(config.CACHE_DIR)
    return ox


def _with_endpoints(fetch):
    """Run ``fetch(ox)`` against each public Overpass endpoint in turn; they are often at capacity."""
    ox = _osmnx()
    last_error: Exception | None = None
    for endpoint in OVERPASS_ENDPOINTS:
        ox.settings.overpass_url = endpoint
        try:
            return fetch(ox)
        except Exception as exc:  # noqa: BLE001 - try the next mirror
            print(f"Overpass endpoint failed ({endpoint}): {type(exc).__name__}")
            last_error = exc
    raise RuntimeError("All Overpass endpoints failed") from last_error


def download_walk_network(bbox: BBox = SOUTHBANK_BBOX, out_path: Path = config.OSM_WALK_PATH) -> Path:
    """Download the *unsimplified* OSM walking network and save it as GraphML.

    Simplification happens at build time so it can respect tag changes along a way.
    """
    ox = _osmnx()
    ox.settings.useful_tags_way = list(dict.fromkeys([*ox.settings.useful_tags_way, *OSM_EXTRA_WAY_TAGS]))
    ox.settings.useful_tags_node = list(dict.fromkeys([*ox.settings.useful_tags_node, *OSM_EXTRA_NODE_TAGS]))
    graph = _with_endpoints(lambda ox: ox.graph_from_bbox(bbox.as_osmnx, network_type="walk",
                                                          simplify=False, retain_all=True))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, out_path)
    return out_path


def load_walk_network(path: Path = config.OSM_WALK_PATH) -> nx.MultiDiGraph:
    """The raw (unsimplified) OSM walking network as an osmnx MultiDiGraph."""
    return _osmnx().load_graphml(path)


def _download_features(path: Path, bbox: BBox, tags: dict, keep: tuple, geom_types: tuple) -> Path:
    gdf = _with_endpoints(lambda ox: ox.features_from_bbox(bbox.as_osmnx, tags=tags))
    gdf = gdf[gdf.geom_type.isin(geom_types)]
    gdf = gdf[[c for c in (*keep, "geometry") if c in gdf.columns]].reset_index()
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GeoJSON")
    return path


def download_buildings(bbox: BBox = SOUTHBANK_BBOX) -> tuple[Path, Path]:
    """Building footprints and entrance nodes."""
    return (_download_features(config.OSM_BUILDINGS_PATH, bbox, {"building": True}, BUILDING_TAGS,
                               ("Polygon", "MultiPolygon")),
            _download_features(config.OSM_ENTRANCES_PATH, bbox, {"entrance": True}, ENTRANCE_TAGS, ("Point",)))


def download_water_and_bridges(bbox: BBox = SOUTHBANK_BBOX) -> tuple[Path, Path]:
    """Water polygons and all bridge ways (any highway/railway); used to validate network topology."""
    return (_download_features(config.OSM_WATER_PATH, bbox,
                               {"natural": "water", "water": "river", "waterway": "riverbank"},
                               ("name", "natural", "water"), ("Polygon", "MultiPolygon")),
            _download_features(config.OSM_BRIDGES_PATH, bbox, {"bridge": True},
                               ("name", "bridge", "bridge:name", "highway", "railway", "layer"),
                               ("LineString", "MultiLineString", "Polygon", "MultiPolygon")))
