"""Download and load pedestrian network data for the study area.

Sources
-------
- City of Melbourne Pedestrian Network (CC BY), via the Opendatasoft Explore API v2.1:
  https://data.melbourne.vic.gov.au/explore/dataset/pedestrian-network/
- OpenStreetMap walking network (ODbL), via osmnx / Overpass API.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import requests

COM_DATASET_URL = (
    "https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/pedestrian-network"
)

# Metric CRS for all geometry work: GDA2020 / MGA zone 55.
METRIC_CRS = "EPSG:7855"
WGS84 = "EPSG:4326"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"


@dataclass(frozen=True)
class BBox:
    """Geographic bounding box in WGS84 degrees."""

    south: float
    west: float
    north: float
    east: float

    @property
    def as_osmnx(self) -> tuple[float, float, float, float]:
        # osmnx >= 2.0 expects (left, bottom, right, top)
        return (self.west, self.south, self.east, self.north)


# Download extent: the CLUE Southbank polygon plus the routing buffer, with margin.
# Includes the north bank of the Yarra so river bridges are covered.
SOUTHBANK_BBOX = BBox(south=-37.8360, west=144.9415, north=-37.8150, east=144.9770)

COM_RAW_PATH = RAW_DIR / "com_pedestrian_network_southbank.geojson"
OSM_RAW_PATH = RAW_DIR / "osm_walk_southbank.graphml"


def download_com_network(bbox: BBox = SOUTHBANK_BBOX, out_path: Path = COM_RAW_PATH) -> Path:
    """Export the CoM pedestrian network records whose centroid lies in ``bbox``."""
    where = f"in_bbox(geo_point_2d,{bbox.south},{bbox.west},{bbox.north},{bbox.east})"
    resp = requests.get(f"{COM_DATASET_URL}/exports/geojson", params={"where": where}, timeout=120)
    resp.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(resp.content)
    return out_path


OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api",
    "https://overpass.private.coffee/api",
    "https://maps.mail.ru/osm/tools/overpass/api",
)


# Extra OSM tags kept on ways/nodes: needed to drop indoor corridors and carriageways that
# duplicate separately mapped sidewalks, and useful later for accessibility (steps, incline, kerbs).
OSM_EXTRA_WAY_TAGS = (
    "footway", "sidewalk", "sidewalk:both", "sidewalk:left", "sidewalk:right", "foot",
    "indoor", "level", "layer", "covered", "surface", "incline", "wheelchair", "crossing",
)
OSM_EXTRA_NODE_TAGS = ("crossing", "entrance", "kerb", "wheelchair", "barrier")


def download_osm_network(bbox: BBox = SOUTHBANK_BBOX, out_path: Path = OSM_RAW_PATH) -> Path:
    """Download the *unsimplified* OSM walking network for ``bbox`` and save it as GraphML.

    Simplification happens at build time so it can respect tag changes along a way.
    Tries each public Overpass endpoint in turn, since they are frequently at capacity.
    """
    import osmnx as ox

    ox.settings.use_cache = True
    ox.settings.cache_folder = str(PROJECT_ROOT / "cache")
    ox.settings.useful_tags_way = list(dict.fromkeys([*ox.settings.useful_tags_way, *OSM_EXTRA_WAY_TAGS]))
    ox.settings.useful_tags_node = list(dict.fromkeys([*ox.settings.useful_tags_node, *OSM_EXTRA_NODE_TAGS]))
    last_error: Exception | None = None
    for endpoint in OVERPASS_ENDPOINTS:
        ox.settings.overpass_url = endpoint
        try:
            graph = ox.graph_from_bbox(
                bbox.as_osmnx, network_type="walk", simplify=False, retain_all=True
            )
            break
        except Exception as exc:  # noqa: BLE001 - try the next mirror
            print(f"Overpass endpoint failed ({endpoint}): {type(exc).__name__}")
            last_error = exc
    else:
        raise RuntimeError("All Overpass endpoints failed") from last_error
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, out_path)
    return out_path


CLUE_DATASET_URL = (
    "https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/"
    "small-areas-for-census-of-land-use-and-employment-clue"
)
CLUE_SOUTHBANK_PATH = RAW_DIR / "clue_southbank_boundary.geojson"

# Routing keeps this much network outside the study area so detours and bridges still work.
STUDY_AREA_BUFFER_M = 250.0


def download_clue_boundary(area_name: str = "Southbank", out_path: Path = CLUE_SOUTHBANK_PATH) -> Path:
    """Export one CoM CLUE small-area polygon (CC BY) as GeoJSON."""
    resp = requests.get(f"{CLUE_DATASET_URL}/exports/geojson",
                        params={"where": f'featurenam="{area_name}"'}, timeout=60)
    resp.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(resp.content)
    return out_path


def load_study_area(path: Path = CLUE_SOUTHBANK_PATH):
    """The study-area polygon in the metric CRS."""
    gdf = gpd.read_file(path).to_crs(METRIC_CRS)
    if len(gdf) != 1:
        raise ValueError(f"Expected one study-area polygon in {path}, found {len(gdf)}")
    return gdf.geometry.iloc[0]


OSM_WATER_PATH = RAW_DIR / "osm_water_southbank.geojson"
OSM_BRIDGES_PATH = RAW_DIR / "osm_bridges_southbank.geojson"


def download_osm_context(bbox: BBox = SOUTHBANK_BBOX) -> tuple[Path, Path]:
    """Download OSM water polygons and all bridge ways (any highway/railway) for ``bbox``."""
    import osmnx as ox

    ox.settings.use_cache = True
    ox.settings.cache_folder = str(PROJECT_ROOT / "cache")
    queries = {
        OSM_WATER_PATH: {"natural": "water", "water": "river", "waterway": "riverbank"},
        OSM_BRIDGES_PATH: {"bridge": True},
    }
    for path, tags in queries.items():
        for endpoint in OVERPASS_ENDPOINTS:
            ox.settings.overpass_url = endpoint
            try:
                gdf = ox.features_from_bbox(bbox.as_osmnx, tags=tags)
                break
            except Exception as exc:  # noqa: BLE001 - try the next mirror
                print(f"Overpass endpoint failed ({endpoint}): {type(exc).__name__}")
        else:
            raise RuntimeError(f"All Overpass endpoints failed for {tags}")
        keep = [c for c in ("name", "bridge", "bridge:name", "highway", "railway", "layer",
                            "natural", "water", "geometry") if c in gdf.columns]
        gdf = gdf[keep].reset_index()
        gdf.to_file(path, driver="GeoJSON")
    return OSM_WATER_PATH, OSM_BRIDGES_PATH


OSM_BUILDINGS_PATH = RAW_DIR / "osm_buildings_southbank.geojson"
OSM_ENTRANCES_PATH = RAW_DIR / "osm_entrances_southbank.geojson"
BUILDING_TAGS = ("name", "building", "addr:housenumber", "addr:street", "level", "layer")
ENTRANCE_TAGS = ("name", "entrance", "door", "access", "level", "indoor", "layer", "wheelchair", "ref")


def _features(bbox: BBox, tags: dict):
    import osmnx as ox

    ox.settings.use_cache = True
    ox.settings.cache_folder = str(PROJECT_ROOT / "cache")
    for endpoint in OVERPASS_ENDPOINTS:
        ox.settings.overpass_url = endpoint
        try:
            return ox.features_from_bbox(bbox.as_osmnx, tags=tags)
        except Exception as exc:  # noqa: BLE001 - try the next mirror
            print(f"Overpass endpoint failed ({endpoint}): {type(exc).__name__}")
    raise RuntimeError(f"All Overpass endpoints failed for {tags}")


def download_osm_buildings(bbox: BBox = SOUTHBANK_BBOX) -> tuple[Path, Path]:
    """Download OSM building footprints and entrance nodes for ``bbox``."""
    out = []
    for path, tags, keep, geom_types in (
        (OSM_BUILDINGS_PATH, {"building": True}, BUILDING_TAGS, ("Polygon", "MultiPolygon")),
        (OSM_ENTRANCES_PATH, {"entrance": True}, ENTRANCE_TAGS, ("Point",)),
    ):
        gdf = _features(bbox, tags)
        gdf = gdf[gdf.geom_type.isin(geom_types)]
        gdf = gdf[[c for c in (*keep, "geometry") if c in gdf.columns]].reset_index()
        path.parent.mkdir(parents=True, exist_ok=True)
        gdf.to_file(path, driver="GeoJSON")
        out.append(path)
    return out[0], out[1]


def load_com_network(path: Path = COM_RAW_PATH) -> gpd.GeoDataFrame:
    """Load the raw CoM export, reprojected to the metric CRS."""
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(WGS84)
    return gdf.to_crs(METRIC_CRS)


def load_osm_network(path: Path = OSM_RAW_PATH):
    """Load the OSM walking network as an osmnx MultiDiGraph."""
    import osmnx as ox

    return ox.load_graphml(path)


if __name__ == "__main__":
    print("CoM  ->", download_com_network())
    print("OSM  ->", download_osm_network())
    print("OSM context ->", download_osm_context())
    print("OSM buildings ->", download_osm_buildings())
