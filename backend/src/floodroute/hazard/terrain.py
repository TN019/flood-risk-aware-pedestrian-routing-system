"""Water depths from ground elevation, for the two flood mechanisms in Southbank.

Melbourne Water's Southbank Precinct Local Floodplain Development Plan describes two mechanisms:
the Yarra River, driven by storm tide in Port Phillip Bay together with river flows, overtopping the
promenade and filling low ground; and short, generally shallow local stormwater flooding, made
worse when high tailwater in the river stops the drains discharging. Each is estimated statically
from a bare-earth elevation model:

- River and tide (``river_inundation``): every ground cell lower than the tide level and connected
  to the river through ground lower than that level is under water ("bathtub with connectivity",
  the usual method for regional coastal inundation mapping). With ``inlets``, drain inlets below
  the tide level also let water in: a high tide backs up through the drains and surcharges around
  the pits (City of Melbourne flood and storm emergency sub-plan), reaching low ground that higher
  ground cuts off from the river.
- Stormwater ponding (``depression_ponding``): rain that the drains cannot take collects in closed
  depressions of the terrain, wherever they are; the plan describes local stormwater flooding as
  shallow but widespread across streets and laneways. A depression full to its spill point is the
  most it can hold before water runs on; ``fill_fraction`` sets how far up from its lowest point
  each depression fills.

This is a static estimate, not a hydraulic model: no flow, velocity, timing or drainage.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
from affine import Affine
from rasterio.features import geometry_mask
from scipy import ndimage

from floodroute.hazard.base import DRY_DEPTH_M
from floodroute.hazard.grid import DepthGrid

WATER_SURFACE_M = 0.05  # DEM cells at or below this are river or dock water surface, not ground
PIT_WINDOW_CELLS = 5  # neighbourhood used to recognise narrow pits (about 25 m across)
PIT_TOLERANCE_M = 0.5  # ground more than this below its neighbourhood median is treated as a pit
GROUND_FILTER_CELLS = 3  # final median smoothing
# Highest astronomical tide at Williamstown, m AHD (Port Phillip Bay Coastal Hazard Assessment, 2023).
# Land the river reaches overland at this level would be flooded by ordinary tides; in Southbank such
# cells are excavations or filled voids in the ground model, so their depth is left unknown.
HIGHEST_TIDE_M = 0.59
EIGHT_NEIGHBOURS = np.ones((3, 3), dtype=bool)


@dataclass(frozen=True)
class Terrain:
    """Walking-surface elevation, metres AHD.

    The raw bare-earth model is adjusted for footpaths: river and dock surface cells take the
    elevation of the nearest bank (paths along a bank otherwise sample the water), and narrow pits
    such as basement ramps and road cuttings are lifted to within ``PIT_TOLERANCE_M`` of their
    surroundings (paths beside them otherwise read metres of water). This can hide water in a
    genuine pedestrian underpass.
    """

    ground_m: np.ndarray
    water: np.ndarray  # True where the raw model shows a water surface
    transform: Affine
    crs: str

    @classmethod
    def read(cls, path: Path) -> Terrain:
        import rasterio

        with rasterio.open(path) as src:
            z = src.read(1).astype("float32")
            if src.nodata is not None:
                z[z == src.nodata] = np.nan
            transform, crs = src.transform, src.crs.to_string()
        return cls(walking_surface(z), z <= WATER_SURFACE_M, transform, crs)

    def mask(self, geometries) -> np.ndarray:
        geoms = [g for g in geometries if g is not None and not g.is_empty]
        if not geoms:
            return np.zeros(self.ground_m.shape, dtype=bool)
        return ~geometry_mask(geoms, out_shape=self.ground_m.shape, transform=self.transform)


def walking_surface(z: np.ndarray) -> np.ndarray:
    water = z <= WATER_SURFACE_M
    if water.any() and (~water).any():
        _, (rows, cols) = ndimage.distance_transform_edt(water, return_indices=True)
        z = z[rows, cols]  # each water cell takes its nearest land cell's elevation
    surroundings = ndimage.median_filter(z, size=PIT_WINDOW_CELLS)
    z = np.maximum(z, surroundings - PIT_TOLERANCE_M)
    return ndimage.median_filter(z, size=GROUND_FILTER_CELLS).astype("float32")


def inlet_cells(terrain: Terrain, inlets: gpd.GeoDataFrame) -> np.ndarray:
    """Grid cells holding at least one drain inlet."""
    from rasterio.transform import rowcol

    points = inlets.to_crs(terrain.crs).geometry
    rows, cols = (np.asarray(v, dtype=int) for v in rowcol(terrain.transform, points.x, points.y))
    shape = terrain.ground_m.shape
    keep = (rows >= 0) & (rows < shape[0]) & (cols >= 0) & (cols < shape[1])
    cells = np.zeros(shape, dtype=bool)
    cells[rows[keep], cols[keep]] = True
    return cells


def river_inundation(terrain: Terrain, level_m: float, inlets: np.ndarray | None = None) -> np.ndarray:
    """Depth of water at ``level_m`` (metres AHD) on ground connected to the river, overland or,
    with ``inlets`` (cells holding a drain inlet), back up through the drains."""
    ground = terrain.ground_m
    lower = ((ground < level_m) & ~np.isnan(ground)) | terrain.water
    labels, _ = ndimage.label(lower, structure=EIGHT_NEIGHBOURS)
    sources = terrain.water if inlets is None else terrain.water | inlets
    reached = np.isin(labels, np.unique(labels[sources & (labels > 0)]))
    return np.where(reached & ~terrain.water, level_m - ground, 0.0).astype("float32")


def spill_elevation(ground: np.ndarray, outlets: np.ndarray) -> np.ndarray:
    """Elevation each cell would have to rise to before water could drain off it, through
    neighbouring cells, to an outlet or the grid edge (priority-flood depression filling)."""
    h, w = ground.shape
    filled = np.where(np.isnan(ground), np.nan, np.inf)
    seeds = outlets.copy()
    seeds[0, :] = seeds[-1, :] = seeds[:, 0] = seeds[:, -1] = True
    seeds &= ~np.isnan(ground)
    filled[seeds] = ground[seeds]
    queue = [(float(ground[r, c]), r, c) for r, c in zip(*np.nonzero(seeds), strict=True)]
    heapq.heapify(queue)
    while queue:
        level, r, c = heapq.heappop(queue)
        for rr in range(max(r - 1, 0), min(r + 2, h)):
            for cc in range(max(c - 1, 0), min(c + 2, w)):
                if filled[rr, cc] == np.inf:
                    filled[rr, cc] = max(level, float(ground[rr, cc]))
                    heapq.heappush(queue, (filled[rr, cc], rr, cc))
    return filled


def depression_ponding(terrain: Terrain, areas: np.ndarray, fill_fraction: float) -> np.ndarray:
    """Depth of stormwater ponded in the depressions inside ``areas``, each filled
    ``fill_fraction`` of the way from its lowest point to its spill point."""
    ground = terrain.ground_m
    full = np.nan_to_num(spill_elevation(ground, terrain.water) - ground)
    ponds, count = ndimage.label(areas & (full > DRY_DEPTH_M), structure=EIGHT_NEIGHBOURS)
    if count == 0:
        return np.zeros(ground.shape, dtype="float32")
    index = np.arange(1, count + 1)
    bottom = np.asarray(ndimage.minimum(ground, ponds, index))
    spill = np.asarray(ndimage.maximum(ground + full, ponds, index))
    level = np.concatenate([[np.nan], bottom + fill_fraction * (spill - bottom)])[ponds]
    return np.where(ponds > 0, np.maximum(level - ground, 0), 0).astype("float32")


def scenario_depths(
    terrain: Terrain,
    tide_level_m: float | None,
    ponding_fill_fraction: float,
    inlets: np.ndarray | None = None,
) -> DepthGrid:
    """Tide (overland, and through ``inlets`` if given) and stormwater ponding together: the deeper
    of the two at each cell."""
    depth = np.zeros(terrain.ground_m.shape, dtype="float32")
    if tide_level_m is not None:
        depth = river_inundation(terrain, tide_level_m, inlets)
    if ponding_fill_fraction > 0:
        depth = np.maximum(depth, depression_ponding(terrain, ~terrain.water, ponding_fill_fraction))
    unreliable = np.isnan(terrain.ground_m) | (river_inundation(terrain, HIGHEST_TIDE_M) > 0)
    depth = np.where(unreliable, np.nan, depth).astype("float32")
    return DepthGrid(depth, terrain.transform, terrain.crs)
