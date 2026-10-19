"""Footpath gradients on the routing graph, from surveyed footpath sections.

Each section (``sources.steepness``) is a footpath polygon with one gradient: the rise between its
lowest and highest surveyed points over the distance between them. An edge takes its ``gradient``
(rise over run) from the sections it runs along:

- Sections whose run is shorter than ``MIN_RUN_M`` are left out. Over a few metres the gradient is
  set by kerb ramps, which AS 1428.1 allows up to 1:8 over at most 1.52 m, and by the precision of
  the levels.
- Sections that may join two levels are not trusted: those within ``MATCH_M`` of a bridge, where a
  footpath polygon can take in both the deck and the bank below it, and those steeper than
  ``STEEPEST_RAMP`` that rise more than ``TWO_LEVEL_RISE_M``. Most of the latter run beside a road
  that climbs onto an overpass, or take in the top and bottom of a flight of steps.
- Bridges and tunnels take no gradient: the sections beside or under them are at another level.
- Every ``SAMPLE_SPACING_M`` along an edge, the gradient there is the gentlest of the trusted
  sections within ``MATCH_M`` (the line and the polygon are drawn a little apart; a section so also
  reaches that far past its ends), so where sections overlap they must agree before a stretch counts
  as steep. The edge's gradient is the steepest one held over ``MIN_STRETCH_M`` in a row (over the
  whole edge, if it is shorter), or ``None`` where no stretch that long lies along a section.

An edge without a gradient is not treated as steep: carriageways, private paths and many park paths
are not in the data, and treating them all as steep would leave wheelchair users almost no routes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields

import geopandas as gpd
import networkx as nx
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from shapely.geometry import LineString
from shapely.strtree import STRtree

STEEPEST_RAMP = 1 / 14  # AS 1428.1: the steepest ramp on an accessible path of travel
MIN_RUN_M = 5.0
MATCH_M = 2.0
TWO_LEVEL_RISE_M = 2.0
SAMPLE_SPACING_M = 1.0
MIN_STRETCH_M = 5.0

TRUSTED, SHORT, NEAR_BRIDGE, TWO_LEVELS = "trusted", "short", "near a bridge", "two levels"


@dataclass
class GradientReport:
    sections: int = 0
    short: int = 0
    near_bridge: int = 0
    two_levels: int = 0
    trusted: int = 0
    trusted_steeper_than_ramp: int = 0
    edges_with_gradient: int = 0
    edges_steeper_than_ramp: int = 0

    def as_dict(self) -> dict[str, int]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


def classify_sections(sections: gpd.GeoDataFrame, graph: nx.Graph) -> list[str]:
    """Whether each section is used (``TRUSTED``) or why it is left out."""
    bridges = [d["geometry"] for *_, d in graph.edges(data=True) if d.get("is_bridge")]
    near_bridge = sections.geometry.buffer(MATCH_M).intersects(gpd.GeoSeries(bridges).union_all()) if bridges else None
    out = []
    for i, s in enumerate(sections.itertuples()):
        if s.run_m < MIN_RUN_M:
            out.append(SHORT)
        elif near_bridge is not None and near_bridge.iloc[i]:
            out.append(NEAR_BRIDGE)
        elif s.gradient > STEEPEST_RAMP and s.rise_m > TWO_LEVEL_RISE_M:
            out.append(TWO_LEVELS)
        else:
            out.append(TRUSTED)
    return out


def add_gradients(graph: nx.Graph, sections: gpd.GeoDataFrame) -> GradientReport:
    """Set ``gradient`` on every edge of ``graph`` (``None`` where it is not known)."""
    status = classify_sections(sections, graph)
    trusted = sections.loc[np.array([s == TRUSTED for s in status], dtype=bool)]
    report = GradientReport(
        sections=len(sections),
        short=status.count(SHORT),
        near_bridge=status.count(NEAR_BRIDGE),
        two_levels=status.count(TWO_LEVELS),
        trusted=len(trusted),
        trusted_steeper_than_ramp=int((trusted.gradient > STEEPEST_RAMP).sum()),
    )
    tree = STRtree(trusted.geometry.buffer(MATCH_M).values)
    gradients = trusted.gradient.to_numpy(dtype=float)
    for *_, d in graph.edges(data=True):
        if d.get("is_bridge") or d.get("is_tunnel"):
            d["gradient"] = None
        else:
            d["gradient"] = edge_gradient(d["geometry"], tree, gradients)
    known = [d["gradient"] for *_, d in graph.edges(data=True) if d["gradient"] is not None]
    report.edges_with_gradient = len(known)
    report.edges_steeper_than_ramp = sum(g > STEEPEST_RAMP for g in known)
    return report


def edge_gradient(line: LineString, tree: STRtree, gradients: np.ndarray) -> float | None:
    """The steepest gradient the sections in ``tree`` agree on over ``MIN_STRETCH_M`` of ``line``."""
    n = max(1, math.ceil(line.length / SAMPLE_SPACING_M))
    points = [line.interpolate(i / n, normalized=True) for i in range(n + 1)]
    point_idx, section_idx = tree.query(points, predicate="intersects")
    local = np.full(n + 1, np.nan)
    np.fmin.at(local, point_idx, gradients[section_idx])  # the gentlest section at each point
    spacing = line.length / n
    window = n + 1 if spacing == 0 else min(n + 1, math.ceil(MIN_STRETCH_M / spacing - 1e-9) + 1)
    held = sliding_window_view(local, window).min(axis=1)  # NaN where part of the stretch has no section
    held = held[~np.isnan(held)]
    return float(held.max()) if held.size else None
