"""Flood conditions from a water-depth raster.

Any gridded depth source fits here: depths derived from terrain and official flood extents
(``hazard.terrain``), or the output of a hydraulic model such as a TUFLOW run. Each network edge
is sampled along its length; it gets its deepest sampled depth and the length wetter than
``DRY_DEPTH_M``.

Bridges are treated as dry: a bare-earth elevation model (and most depth grids built on one)
shows the water or ground *under* a deck, not the deck itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import networkx as nx
import numpy as np
from affine import Affine
from pyproj import Transformer

from floodroute.hazard.base import DRY, DRY_DEPTH_M, EdgeCondition, HazardSnapshot

SAMPLE_SPACING_M = 2.0


@dataclass(frozen=True)
class DepthGrid:
    depth_m: np.ndarray  # 2-D, metres; NaN = no data
    transform: Affine  # pixel -> grid CRS
    crs: str

    @classmethod
    def read(cls, path: Path) -> DepthGrid:
        import rasterio

        with rasterio.open(path) as src:
            data = src.read(1).astype("float32")
            if src.nodata is not None:
                data[data == src.nodata] = np.nan
            return cls(data, src.transform, src.crs.to_string())

    def write(self, path: Path) -> None:
        import rasterio

        path.parent.mkdir(parents=True, exist_ok=True)
        profile = {
            "driver": "GTiff",
            "height": self.depth_m.shape[0],
            "width": self.depth_m.shape[1],
            "count": 1,
            "dtype": "float32",
            "crs": self.crs,
            "transform": self.transform,
            "nodata": np.nan,
            "compress": "deflate",
            "predictor": 3,
        }
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(self.depth_m.astype("float32"), 1)

    def sample(self, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
        """Depth at grid-CRS coordinates; NaN where the grid has no data or does not reach
        (unknown, never assumed dry)."""
        from rasterio.transform import rowcol

        rows, cols = (np.asarray(v, dtype=int) for v in rowcol(self.transform, xs, ys))
        inside = (rows >= 0) & (rows < self.depth_m.shape[0]) & (cols >= 0) & (cols < self.depth_m.shape[1])
        out = np.full(len(xs), np.nan, dtype="float32")
        out[inside] = self.depth_m[rows[inside], cols[inside]]
        return out


def edge_conditions(grid: DepthGrid, graph: nx.Graph) -> dict[str, EdgeCondition]:
    """Conditions for every wet edge of ``graph`` (metric CRS) under ``grid``."""
    to_grid = Transformer.from_crs(graph.graph["crs"], grid.crs, always_xy=True)
    ids, owners, xs, ys, steps = [], [], [], [], []
    for *_, d in graph.edges(data=True):
        if d.get("is_bridge"):
            continue
        geom = d["geometry"]
        n = max(2, int(np.ceil(geom.length / SAMPLE_SPACING_M)) + 1)
        pts = [geom.interpolate(t) for t in np.linspace(0, geom.length, n)]
        owners.extend([len(ids)] * n)
        xs.extend(p.x for p in pts)
        ys.extend(p.y for p in pts)
        steps.append(geom.length / n)
        ids.append(d["edge_id"])
    gx, gy = to_grid.transform(np.asarray(xs), np.asarray(ys))
    depth = grid.sample(np.asarray(gx), np.asarray(gy))
    owners = np.asarray(owners)
    conditions = {}
    for i in np.unique(owners[np.nan_to_num(depth, nan=1.0) > DRY_DEPTH_M]):
        d = depth[owners == i]
        if np.isnan(d).any():
            conditions[ids[i]] = EdgeCondition(depth_m=None)  # unknown somewhere along the edge
            continue
        wet = int((d > DRY_DEPTH_M).sum())
        conditions[ids[i]] = EdgeCondition(depth_m=round(float(d.max()), 4), flooded_length_m=round(wet * steps[i], 2))
    return conditions


class GridHazard:
    """``HazardProvider`` for a static depth grid."""

    def __init__(self, grid: DepthGrid, source: str):
        self.grid = grid
        self.source = source
        self._cache: dict[int, HazardSnapshot] = {}

    def snapshot(self, graph: nx.Graph, at: datetime | None = None) -> HazardSnapshot:
        key = id(graph)
        if key not in self._cache:
            self._cache[key] = HazardSnapshot(self.source, None, edge_conditions(self.grid, graph), default=DRY)
        snap = self._cache[key]
        return HazardSnapshot(snap.source, at, snap.conditions, snap.default)
