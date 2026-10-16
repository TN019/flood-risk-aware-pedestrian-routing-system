"""Address / place search restricted to the study area, via OpenStreetMap Nominatim.

Nominatim's usage policy: identify the application, at most one request per second, and
cache results. Callers should cache (the app does) and only search on explicit user action.
https://operations.osmfoundation.org/policies/nominatim/
"""

from __future__ import annotations

from dataclasses import dataclass

import requests
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = (
    "flood-risk-aware-pedestrian-routing/0.1 (+https://github.com/TN019/flood-risk-aware-pedestrian-routing-system)"
)


@dataclass(frozen=True)
class SearchResult:
    label: str
    lat: float
    lon: float
    footprint: BaseGeometry | None = None  # WGS84 polygon of the place, when OSM maps it as an area


def search(query: str, viewbox: tuple[float, float, float, float], limit: int = 5) -> list[SearchResult]:
    """Search for ``query`` inside ``viewbox`` = (west, south, east, north) in WGS84 degrees."""
    query = query.strip()
    if not query:
        return []
    west, south, east, north = viewbox
    resp = requests.get(
        NOMINATIM_URL,
        params={
            "q": query,
            "format": "jsonv2",
            "limit": limit,
            "countrycodes": "au",
            "polygon_geojson": 1,
            "viewbox": f"{west},{north},{east},{south}",
            "bounded": 1,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=10,
    )
    resp.raise_for_status()
    results = []
    for r in resp.json():
        geom = r.get("geojson")
        footprint = shape(geom) if geom and geom.get("type") in ("Polygon", "MultiPolygon") else None
        results.append(SearchResult(r["display_name"], float(r["lat"]), float(r["lon"]), footprint))
    return results
