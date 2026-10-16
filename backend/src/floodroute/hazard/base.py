"""Flood conditions on the network, independent of where they come from.

A ``HazardProvider`` produces a ``HazardSnapshot``: the water conditions on each network edge at a
point in time. Routing only ever sees snapshots, so the source can change without touching it:

- mock flood scenarios (synthetic events for testing and illustration),
- real-time sensor readings,
- forecasts from a prediction model (see ``floodroute.prediction``), one snapshot per horizon.

Missing data is explicit: an edge without an entry takes the snapshot's ``default`` condition,
which a provider sets to ``DRY`` only when it actually knows unlisted edges are dry.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

import networkx as nx


@dataclass(frozen=True)
class EdgeCondition:
    depth_m: float | None  # deepest water along the edge; None = unknown
    velocity_m_s: float | None = None
    flooded_length_m: float | None = None  # length under water; None = the whole edge

    @property
    def is_known(self) -> bool:
        return self.depth_m is not None


DRY = EdgeCondition(depth_m=0.0, velocity_m_s=0.0)
UNKNOWN = EdgeCondition(depth_m=None)


@dataclass(frozen=True)
class HazardSnapshot:
    source: str
    time: datetime | None = None
    conditions: Mapping[str, EdgeCondition] = field(default_factory=dict)  # keyed by edge_id
    default: EdgeCondition = UNKNOWN

    def condition(self, edge_id: str) -> EdgeCondition:
        return self.conditions.get(edge_id, self.default)


class HazardProvider(Protocol):
    def snapshot(self, graph: nx.Graph, at: datetime | None = None) -> HazardSnapshot:
        """Conditions on ``graph``'s edges at time ``at`` (None = now)."""
        ...


class NoHazard:
    """Every edge is dry. The baseline for routing without flood information."""

    def snapshot(self, graph: nx.Graph, at: datetime | None = None) -> HazardSnapshot:
        return HazardSnapshot(source="none", time=at, default=DRY)
