"""Sheltered refuges: buildings a traveller can go into and wait while water recedes.

Every building with a way in counts: its usable outdoor entrances, or, where none are mapped, the
points on its outline nearest the footpaths (the same rules as for destinations). Whether a
building is open to the public is not known from the data, so this is an optimistic assumption.
Refuges are judged on current conditions only; the model does not know whether water will rise.
"""

from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree

from floodroute.places.resolver import DESTINATION, AccessPoint, PlaceResolver

SEARCH_RADIUS_M = 800.0  # refuges further than this (straight line) are not considered
MAX_CANDIDATES = 25  # nearest buildings offered to the router at once


UNNAMED = "Building"  # the name of a refuge whose building has none


@dataclass(frozen=True)
class Refuge:
    name: str  # UNNAMED when the building has no name
    building: BaseGeometry
    access: tuple[AccessPoint, ...]
    named: bool = True


class RefugeIndex:
    def __init__(self, resolver: PlaceResolver, area: BaseGeometry | None = None):
        """``area``: only buildings intersecting it are refuges (e.g. the routable area)."""
        self.resolver = resolver
        buildings = resolver.buildings
        if area is not None:
            buildings = buildings[buildings.intersects(area)]
        self._geoms = list(buildings.geometry)
        self._names = [n if isinstance(n, str) else None for n in buildings.get("name", [None] * len(buildings))]
        self._tree = STRtree(self._geoms)
        self._cache: dict[int, Refuge | None] = {}

    def __len__(self) -> int:
        return len(self._geoms)

    def refuge(self, i: int) -> Refuge | None:
        if i not in self._cache:
            building = self._geoms[i]
            access = self.resolver.entrances_of(building, DESTINATION) or self.resolver.outline_points(building)
            name = self._names[i]
            self._cache[i] = Refuge(name or UNNAMED, building, tuple(access), name is not None) if access else None
        return self._cache[i]

    def nearest(self, point: Point, radius_m: float = SEARCH_RADIUS_M, limit: int = MAX_CANDIDATES) -> list[Refuge]:
        """Refuges within ``radius_m`` of ``point``, nearest first, skipping any the point is inside."""
        idx = self._tree.query(point.buffer(radius_m))
        ranked = sorted(idx, key=lambda i: self._geoms[i].distance(point))
        out = []
        for i in ranked:
            if self._geoms[i].contains(point):
                continue
            refuge = self.refuge(i)
            if refuge is not None:
                out.append(refuge)
            if len(out) == limit:
                break
        return out
