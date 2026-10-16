"""Hand-drawn flood zones turned into edge conditions, for tests and what-if experiments.

The bundled scenarios are built from official flood extents and terrain instead
(``hazard.catalog``, ``hazard.terrain``).

A scenario is a GeoJSON FeatureCollection (WGS84) of polygon flood zones with top-level members
``id``, ``title``, ``description`` and ``order`` (severity rank, 0 = normal). Each zone has
properties ``name``, ``max_depth_m`` and ``ramp_m``: water is 0 m deep at the zone's edge and
deepens linearly inward, reaching ``max_depth_m`` at ``ramp_m`` from the edge. Overlapping zones
take the deeper value.

Each network edge gets its deepest sampled depth and the length that is wetter than
``DRY_DEPTH_M``. Edges outside every zone are dry: a scenario fully specifies its own water.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import networkx as nx
import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.strtree import STRtree

from floodroute import config
from floodroute.hazard.base import DRY, DRY_DEPTH_M, EdgeCondition, HazardSnapshot

SAMPLE_SPACING_M = 1.0  # depth is sampled along flooded edges at this spacing


@dataclass(frozen=True)
class FloodZone:
    name: str
    polygon: BaseGeometry  # metric CRS
    max_depth_m: float
    ramp_m: float

    def depth_at(self, point: Point) -> float:
        if not self.polygon.covers(point):
            return 0.0
        inward = self.polygon.boundary.distance(point)
        return self.max_depth_m * min(1.0, inward / self.ramp_m) if self.ramp_m > 0 else self.max_depth_m


@dataclass(frozen=True)
class FloodScenario:
    id: str
    title: str
    description: str
    zones: tuple[FloodZone, ...]
    order: int = 0

    def depth_at(self, point: Point) -> float:
        return max((z.depth_at(point) for z in self.zones), default=0.0)


def load_scenario(path: Path, crs: str = config.METRIC_CRS) -> FloodScenario:
    doc = json.loads(Path(path).read_text())
    to_crs = Transformer.from_crs(config.WGS84, crs, always_xy=True)
    project = lambda xy: np.column_stack(to_crs.transform(xy[:, 0], xy[:, 1]))  # noqa: E731
    zones = []
    for f in doc["features"]:
        props = f["properties"]
        zones.append(
            FloodZone(
                props["name"],
                shapely.transform(shape(f["geometry"]), project),
                float(props["max_depth_m"]),
                float(props.get("ramp_m", 0.0)),
            )
        )
    return FloodScenario(
        doc.get("id", Path(path).stem),
        doc.get("title", Path(path).stem),
        doc.get("description", ""),
        tuple(zones),
        int(doc.get("order", 0)),
    )


def edge_condition(scenario: FloodScenario, geometry: BaseGeometry, flooded_area: BaseGeometry) -> EdgeCondition:
    """Deepest depth and wet length of one edge."""
    wet_part = geometry.intersection(flooded_area)
    if wet_part.is_empty or wet_part.length == 0:
        return DRY
    lines = getattr(wet_part, "geoms", [wet_part])
    deepest, wet = 0.0, 0.0
    for line in lines:
        if line.length == 0:
            continue
        n = max(2, int(np.ceil(line.length / SAMPLE_SPACING_M)) + 1)
        depths = [scenario.depth_at(line.interpolate(d)) for d in np.linspace(0, line.length, n)]
        deepest = max(deepest, *depths)
        wet += line.length * sum(d > DRY_DEPTH_M for d in depths) / n
    if deepest <= DRY_DEPTH_M:
        return DRY
    return EdgeCondition(depth_m=round(deepest, 4), flooded_length_m=round(wet, 2))


class ScenarioHazard:
    """``HazardProvider`` for a synthetic scenario. Conditions do not change over time."""

    def __init__(self, scenario: FloodScenario):
        self.scenario = scenario
        self._flooded = unary_union([z.polygon for z in scenario.zones]) if scenario.zones else None
        self._cache: dict[int, HazardSnapshot] = {}

    def snapshot(self, graph: nx.Graph, at: datetime | None = None) -> HazardSnapshot:
        key = id(graph)
        if key not in self._cache:
            conditions = {}
            if self._flooded is not None:
                edges = [d for *_, d in graph.edges(data=True)]
                tree = STRtree([d["geometry"] for d in edges])
                for i in tree.query(self._flooded, predicate="intersects"):
                    cond = edge_condition(self.scenario, edges[i]["geometry"], self._flooded)
                    if cond is not DRY:
                        conditions[edges[i]["edge_id"]] = cond
            self._cache[key] = HazardSnapshot(source=f"scenario:{self.scenario.id}", conditions=conditions, default=DRY)
        snap = self._cache[key]
        return HazardSnapshot(snap.source, at, snap.conditions, snap.default)
