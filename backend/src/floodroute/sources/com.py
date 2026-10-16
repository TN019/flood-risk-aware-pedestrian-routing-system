"""City of Melbourne open data (CC BY) via the Opendatasoft Explore API v2.1.

- Pedestrian Network: https://data.melbourne.vic.gov.au/explore/dataset/pedestrian-network/
  An alternative network source; the OSM walking network is the primary one.
- CLUE small areas: the official Southbank boundary used as the study area.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry.base import BaseGeometry

from floodroute import config
from floodroute.config import SOUTHBANK_BBOX, BBox

API = "https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets"
PEDESTRIAN_NETWORK_DATASET = f"{API}/pedestrian-network"
CLUE_DATASET = f"{API}/small-areas-for-census-of-land-use-and-employment-clue"


def _export(url: str, params: dict, out_path: Path, timeout: int = 120) -> Path:
    resp = requests.get(f"{url}/exports/geojson", params=params, timeout=timeout)
    resp.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(resp.content)
    return out_path


def download_pedestrian_network(bbox: BBox = SOUTHBANK_BBOX, out_path: Path = config.COM_NETWORK_PATH) -> Path:
    """Pedestrian network records whose centroid lies in ``bbox``."""
    where = f"in_bbox(geo_point_2d,{bbox.south},{bbox.west},{bbox.north},{bbox.east})"
    return _export(PEDESTRIAN_NETWORK_DATASET, {"where": where}, out_path)


def load_pedestrian_network(path: Path = config.COM_NETWORK_PATH) -> gpd.GeoDataFrame:
    """The raw pedestrian network export (LineStrings + parcel Points) in the metric CRS."""
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(config.WGS84)
    return gdf.to_crs(config.METRIC_CRS)


def download_clue_boundary(area_name: str = "Southbank", out_path: Path = config.CLUE_SOUTHBANK_PATH) -> Path:
    """One CLUE small-area polygon."""
    return _export(CLUE_DATASET, {"where": f'featurenam="{area_name}"'}, out_path, timeout=60)


def load_study_area(path: Path = config.CLUE_SOUTHBANK_PATH) -> BaseGeometry:
    """The study-area polygon in the metric CRS."""
    gdf = gpd.read_file(path).to_crs(config.METRIC_CRS)
    if len(gdf) != 1:
        raise ValueError(f"Expected one study-area polygon in {path}, found {len(gdf)}")
    return gdf.geometry.iloc[0]
