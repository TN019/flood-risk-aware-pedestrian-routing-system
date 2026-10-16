"""Ground elevation and official flood extents for the study area.

- Elevation: Geoscience Australia, *Digital Elevation Model (DEM) of Australia derived from LiDAR
  5 Metre Grid* (bare earth, metres AHD), WCS service ``DEM_LiDAR_5m_2025``. Licensed CC BY 4.0.
  The service rejects large requests, so the area is fetched as small tiles and mosaicked.
- Flood extents: Vicmap Planning, *Planning Scheme Overlay Polygon* (``plan_overlay``), CC BY 4.0.
  Land Subject to Inundation Overlay (LSIO, riverine and main-drain flooding) and Special Building
  Overlay (SBO, overland flow) mark land expected to flood in a 1% annual exceedance probability
  (1-in-100-year) event. They give extents only, not depths.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import requests

from floodroute import config
from floodroute.config import SOUTHBANK_BBOX, BBox

DEM_WCS = "https://services.ga.gov.au/gis/services/DEM_LiDAR_5m_2025/MapServer/WCSServer"
DEM_TILE_DEG = 0.005  # about 440 m x 555 m per request; larger requests are refused
DEM_RES_DEG = 0.00005  # about 5 m, the native resolution

VICMAP_WFS = "https://opendata.maps.vic.gov.au/geoserver/wfs"
FLOOD_OVERLAY_PREFIXES = ("LSIO", "SBO", "FO")  # inundation, special building, floodway overlays


def download_dem(bbox: BBox = SOUTHBANK_BBOX, out_path: Path = config.DEM_PATH) -> Path:
    import rasterio
    from rasterio.merge import merge

    xs = np.arange(bbox.west, bbox.east, DEM_TILE_DEG)
    ys = np.arange(bbox.south, bbox.north, DEM_TILE_DEG)
    with tempfile.TemporaryDirectory() as tmp:
        tiles = []
        for x0 in xs:
            for y0 in ys:
                x1, y1 = min(x0 + DEM_TILE_DEG, bbox.east), min(y0 + DEM_TILE_DEG, bbox.north)
                params = (
                    "service=WCS&version=1.0.0&request=GetCoverage&coverage=1&crs=EPSG:4283"
                    f"&bbox={x0:.6f},{y0:.6f},{x1:.6f},{y1:.6f}&resx={DEM_RES_DEG}&resy={DEM_RES_DEG}&format=GeoTIFF"
                )
                resp = requests.get(f"{DEM_WCS}?{params}", timeout=120)
                resp.raise_for_status()
                if not resp.content.startswith((b"II*", b"MM\0*")):
                    raise RuntimeError(f"DEM service returned no GeoTIFF for tile {x0:.4f},{y0:.4f}")
                path = Path(tmp) / f"tile_{len(tiles)}.tif"
                path.write_bytes(resp.content)
                tiles.append(path)
        sources = [rasterio.open(p) for p in tiles]
        try:
            mosaic, transform = merge(sources)
            profile = sources[0].profile | {
                "height": mosaic.shape[1],
                "width": mosaic.shape[2],
                "transform": transform,
                "compress": "deflate",
            }
        finally:
            for s in sources:
                s.close()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(mosaic)
    return out_path


def download_flood_overlays(bbox: BBox = SOUTHBANK_BBOX, out_path: Path = config.FLOOD_OVERLAYS_PATH) -> Path:
    codes = " OR ".join(f"zone_code LIKE '{p}%'" for p in FLOOD_OVERLAY_PREFIXES)
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": "open-data-platform:plan_overlay",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "CQL_FILTER": f"BBOX(geom,{bbox.west},{bbox.south},{bbox.east},{bbox.north},'EPSG:4326') AND ({codes})",
    }
    resp = requests.get(VICMAP_WFS, params=params, timeout=180)
    resp.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(resp.content)
    return out_path
