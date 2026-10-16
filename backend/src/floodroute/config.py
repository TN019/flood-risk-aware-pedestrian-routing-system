"""Project-wide settings: coordinate systems, study area, and data file locations.

The data directory defaults to ``<repo>/data`` and can be moved with ``FLOODROUTE_DATA_DIR``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Metric CRS for all geometry work: GDA2020 / MGA zone 55.
METRIC_CRS = "EPSG:7855"
WGS84 = "EPSG:4326"

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.environ.get("FLOODROUTE_DATA_DIR", REPO_ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SCENARIO_DIR = DATA_DIR / "scenarios"
REPORT_DIR = REPO_ROOT / "reports"
CACHE_DIR = REPO_ROOT / "cache"


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

# Routing keeps this much network outside the study area so detours and bridges still work.
STUDY_AREA_BUFFER_M = 250.0

# Raw inputs (downloaded by scripts/download_data.py)
CLUE_SOUTHBANK_PATH = RAW_DIR / "clue_southbank_boundary.geojson"
OSM_WALK_PATH = RAW_DIR / "osm_walk_southbank.graphml"
OSM_BUILDINGS_PATH = RAW_DIR / "osm_buildings_southbank.geojson"
OSM_ENTRANCES_PATH = RAW_DIR / "osm_entrances_southbank.geojson"
OSM_WATER_PATH = RAW_DIR / "osm_water_southbank.geojson"
OSM_BRIDGES_PATH = RAW_DIR / "osm_bridges_southbank.geojson"
COM_NETWORK_PATH = RAW_DIR / "com_pedestrian_network_southbank.geojson"

# Processed outputs (built by scripts/build_network.py)
PROCESSED_NETWORK_PATH = PROCESSED_DIR / "southbank_network.gpkg"
PROCESSED_COM_NETWORK_PATH = PROCESSED_DIR / "southbank_network_com.gpkg"
PROCESSED_PLACES_PATH = PROCESSED_DIR / "southbank_places.gpkg"
