"""Stormwater drainage pits for the study area.

City of Melbourne open data, *Stormwater Pits* (``stormwater-pits``), licensed CC BY 4.0: location
and type of every council drainage pit, without surface or invert levels. Surface inlets (grates,
side-entry and lane pits) are where water enters the drains in rain and where it comes back up when
a high tide stops the drains discharging to the Yarra.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import requests

from floodroute import config
from floodroute.config import SOUTHBANK_BBOX, BBox

PITS_EXPORT = "https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/stormwater-pits/exports/geojson"
# Pit types that open to the surface; junctions, nodes and submerged pits do not.
SURFACE_INLET_KEYWORDS = ("Grated", "Side Entry", "Lane Type", "Trench Grate", "OFK", "GSEP", "Inlet")
TYPE_FIELD = "object_type_lupvalue"


def download_stormwater_pits(bbox: BBox = SOUTHBANK_BBOX, out_path: Path = config.STORMWATER_PITS_PATH) -> Path:
    where = f"in_bbox(location,{bbox.south},{bbox.west},{bbox.north},{bbox.east})"
    response = requests.get(PITS_EXPORT, params={"where": where}, timeout=120)
    response.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(response.content)
    return out_path


def is_surface_inlet(pit_type) -> bool:
    if not isinstance(pit_type, str):
        return False
    return "Outlet" not in pit_type and any(k in pit_type for k in SURFACE_INLET_KEYWORDS)


def surface_inlets(path: Path = config.STORMWATER_PITS_PATH) -> gpd.GeoDataFrame:
    pits = gpd.read_file(path)
    return pits[pits[TYPE_FIELD].map(is_surface_inlet)]
