"""Turn a chosen place into the points where a pedestrian actually joins the footpath network.

A searched-for place or a map click often lands *inside* a building (Nominatim puts Crown
Melbourne in the middle of the complex). Routing to that point means a long straight "access leg"
through the building. Instead, a place inside a building is represented by the building's usable
outdoor entrances (from OSM ``entrance=*``), and, where none are mapped, by the points on the
building outline closest to the footpath network. The router then picks whichever is cheapest.
"""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points, unary_union
from shapely.strtree import STRtree

ENTRANCE_ON_OUTLINE_M = 1.5  # an entrance node this close to a building outline belongs to it
OUTLINE_SEARCH_M = 60.0  # look for footpaths this far from a building without mapped entrances
OUTLINE_POINT_SPACING_M = 15.0  # outline access points closer than this are duplicates
MAX_ACCESS_POINTS = 8
FOOTPRINT_SHARE = 0.5  # a building belongs to a searched footprint if this share of it lies inside

NOT_FOR_ARRIVING = {"emergency", "service", "garage", "exit", "construction", "subway_entrance"}
NOT_FOR_LEAVING = {"emergency", "service", "garage", "construction", "subway_entrance"}
PRIVATE_ACCESS = {"private", "no", "permit", "delivery"}

ORIGIN, DESTINATION = "origin", "destination"
# Kinds of access point.
MAIN_ENTRANCE, ENTRANCE, BUILDING_EDGE, CHOSEN_POINT = "main_entrance", "entrance", "building_edge", "chosen_point"


@dataclass(frozen=True)
class AccessPoint:
    point: Point
    kind: str  # MAIN_ENTRANCE, ENTRANCE, BUILDING_EDGE or CHOSEN_POINT
    name: str | None = None  # an entrance's own name, if it has one

    @property
    def label(self) -> str:
        """In English, e.g. "main entrance", "entrance (Riverside)", "building edge"."""
        words = self.kind.replace("_", " ")
        return f"{words} ({self.name})" if self.name else words


@dataclass(frozen=True)
class Place:
    label: str
    point: Point  # what the user picked
    access: tuple[AccessPoint, ...]  # where routing may start/end
    building: BaseGeometry | None
    method: str  # "point" | "entrances" | "outline"

    @property
    def access_points(self) -> list[Point]:
        return [a.point for a in self.access]

    def access_at(self, point: Point) -> AccessPoint:
        """The access point nearest to ``point`` (where a route starts or ends)."""
        return min(self.access, key=lambda a: a.point.distance(point))

    def access_label(self, point: Point) -> str:
        return self.access_at(point).label


class PlaceResolver:
    def __init__(self, buildings: gpd.GeoDataFrame, entrances: gpd.GeoDataFrame, footpaths: list[BaseGeometry]):
        """``buildings``/``entrances``: OSM layers in the routing CRS. ``footpaths``: snappable edges."""
        self.buildings = buildings.reset_index(drop=True)
        self.entrances = entrances.reset_index(drop=True)
        self._b_tree = STRtree(list(self.buildings.geometry))
        self._e_tree = STRtree(list(self.entrances.geometry))
        self._footpaths = footpaths
        self._f_tree = STRtree(footpaths)

    # ------------------------------------------------------------------ public

    def resolve(
        self, point: Point, label: str, footprint: BaseGeometry | None = None, role: str = DESTINATION
    ) -> Place:
        building, name = self.building_at(point, footprint)
        if building is None:
            return Place(label, point, (AccessPoint(point, CHOSEN_POINT),), None, "point")
        label = name or label
        access = self.entrances_of(building, role)
        if access:
            return Place(label, point, tuple(access), building, "entrances")
        access = self.outline_points(building)
        if access:
            return Place(label, point, tuple(access), building, "outline")
        return Place(label, point, (AccessPoint(point, CHOSEN_POINT),), building, "point")

    def building_at(
        self, point: Point, footprint: BaseGeometry | None = None
    ) -> tuple[BaseGeometry | None, str | None]:
        """The building (or union of buildings) a place refers to, and its name if known."""
        if footprint is not None and footprint.area > 0:
            idx = [
                i
                for i in self._b_tree.query(footprint)
                if self.buildings.geometry[i].intersection(footprint).area
                >= FOOTPRINT_SHARE * self.buildings.geometry[i].area
            ]
            if idx:
                return unary_union([self.buildings.geometry[i] for i in idx]), None
            return footprint, None
        idx = [i for i in self._b_tree.query(point, predicate="within")]
        if not idx:
            return None, None
        i = min(idx, key=lambda j: self.buildings.geometry[j].area)  # the most specific building
        name = self.buildings.at[i, "name"] if "name" in self.buildings else None
        return self.buildings.geometry[i], (name if isinstance(name, str) else None)

    def entrances_of(self, building: BaseGeometry, role: str = DESTINATION) -> list[AccessPoint]:
        excluded = NOT_FOR_ARRIVING if role == DESTINATION else NOT_FOR_LEAVING
        outline = building.boundary
        out = []
        for i in self._e_tree.query(building.buffer(ENTRANCE_ON_OUTLINE_M)):
            row = self.entrances.iloc[i]
            if row.geometry.distance(outline) > ENTRANCE_ON_OUTLINE_M:
                continue
            if _tag(row, "entrance") in excluded or _tag(row, "access") in PRIVATE_ACCESS:
                continue
            if row.get("indoor_only") == True:  # noqa: E712 - numpy bool or NaN read from file
                continue
            level = _tag(row, "level")
            if level not in (None, "0"):  # upper floors / basements are not reachable from the street
                continue
            kind = _tag(row, "entrance")
            name = _tag(row, "name")
            out.append(AccessPoint(row.geometry, MAIN_ENTRANCE if kind == "main" else ENTRANCE, name))
        return out[: MAX_ACCESS_POINTS * 2]

    def outline_points(self, building: BaseGeometry) -> list[AccessPoint]:
        """Points on the building outline nearest to the surrounding footpaths."""
        outline = building.boundary
        candidates = []
        for i in self._f_tree.query(building.buffer(OUTLINE_SEARCH_M)):
            on_outline, on_path = nearest_points(outline, self._footpaths[i])
            candidates.append((on_outline.distance(on_path), on_outline))
        picked: list[Point] = []
        for _, p in sorted(candidates, key=lambda c: c[0]):
            if all(p.distance(q) >= OUTLINE_POINT_SPACING_M for q in picked):
                picked.append(p)
            if len(picked) == MAX_ACCESS_POINTS:
                break
        return [AccessPoint(p, BUILDING_EDGE) for p in picked]


def _tag(row, key: str) -> str | None:
    value = row.get(key) if hasattr(row, "get") else None
    return value if isinstance(value, str) else None


def mark_indoor_entrances(entrances: gpd.GeoDataFrame, raw_walk_graph) -> gpd.GeoDataFrame:
    """Add ``indoor_only``: the entrance node sits on the OSM walk network but every way through it
    is indoor (a corridor or ``indoor=*``), so it cannot be reached from the street."""
    from floodroute.network.osm_builder import _is_indoor  # osmnx is only needed at build time

    flags = []
    for element, osm_id in zip(entrances["element"], entrances["id"], strict=True):
        n = int(osm_id)
        if element != "node" or n not in raw_walk_graph:
            flags.append(False)
            continue
        ways = [d for _, _, d in raw_walk_graph.edges(n, data=True)] + [
            d for _, _, d in raw_walk_graph.in_edges(n, data=True)
        ]
        flags.append(bool(ways) and all(_is_indoor(d) for d in ways))
    return entrances.assign(indoor_only=flags)
