"""Footpath gradients for the study area.

City of Melbourne open data, *Footpath steepness* (``footpath-steepness``), licensed CC BY: the
gradient of each council footpath section, as a polygon of the footpath. The gradient is the rise
between the section's lowest and highest surveyed levels (``rlmin``, ``rlmax``, m AHD) over the
horizontal distance between those two points (``distance``): ``gradepc = deltaz / distance × 100``.

A section is one footpath asset (``mcc_id``). The export splits many sections into several polygon
pieces that repeat the same values, so ``load_footpath_sections`` merges them back into one row.
Records without a gradient are left out.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import requests

from floodroute import config
from floodroute.config import SOUTHBANK_BBOX, BBox

STEEPNESS_EXPORT = (
    "https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/footpath-steepness/exports/geojson"
)
SECTION_FIELDS = {  # export field -> column of a section
    "mcc_id": "section_id",
    "distance": "run_m",
    "deltaz": "rise_m",
    "rlmin": "level_min_m",
    "rlmax": "level_max_m",
}


def download_footpath_steepness(bbox: BBox = SOUTHBANK_BBOX, out_path: Path = config.FOOTPATH_STEEPNESS_PATH) -> Path:
    where = f"in_bbox(geo_point_2d,{bbox.south},{bbox.west},{bbox.north},{bbox.east})"
    response = requests.get(STEEPNESS_EXPORT, params={"where": where}, timeout=120)
    response.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(response.content)
    return out_path


def load_footpath_sections(path: Path = config.FOOTPATH_STEEPNESS_PATH) -> gpd.GeoDataFrame:
    """One row per footpath section with a measured gradient, in the metric CRS: ``section_id``,
    ``gradient`` (rise over run, e.g. 0.05 for 1:20), ``run_m``, ``rise_m``, ``level_min_m``,
    ``level_max_m``, ``address`` and the merged polygon."""
    raw = gpd.read_file(path)
    if raw.crs is None:
        raw = raw.set_crs(config.WGS84)
    raw = raw[raw.geometry.notna() & raw["gradepc"].notna()].to_crs(config.METRIC_CRS)
    raw = raw.assign(gradient=(raw["gradepc"] / 100).round(4)).rename(columns=SECTION_FIELDS)
    keys = ["section_id", "gradient", *[c for c in SECTION_FIELDS.values() if c != "section_id"]]
    sections = raw[[*keys, "address", "geometry"]].dissolve(by=keys, aggfunc="first", as_index=False)
    return sections.reset_index(drop=True)
