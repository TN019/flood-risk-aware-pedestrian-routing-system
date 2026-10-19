"""What the web API does, independent of HTTP: load the routing data once and answer requests.

Everything leaving this module is plain JSON-ready data in WGS84 (GeoJSON geometries, coordinates
rounded to about 0.1 m). Everything entering it is checked: points must lie inside the study area.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from functools import lru_cache

import geopandas as gpd
import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import LineString, Point, mapping, shape
from shapely.geometry.base import BaseGeometry

from floodroute import config
from floodroute.hazard import HazardProvider
from floodroute.hazard.catalog import ScenarioInfo
from floodroute.network import is_snappable
from floodroute.places import Place, PlaceResolver
from floodroute.places.refuges import RefugeIndex
from floodroute.places.resolver import DESTINATION, ORIGIN
from floodroute.risk import DRY_DEPTH_M, HARD_LIMIT_M, BodyPart, MobilityAid, TravellerProfile
from floodroute.risk.alerts import AlertLevel
from floodroute.risk.levels import REFERENCE_HEIGHT_M, FloodLevel, level_of, typical_depth_m
from floodroute.risk.preference import DEFAULT_PREFERENCE, RoutePreference, explain
from floodroute.risk.profile import LANDMARKS
from floodroute.routing import RECOMMENDED, SAFE_SHORTEST, SHORTEST, Route, RouteMetrics, Router, RoutingError
from floodroute.sources import geocoding
from floodroute.trip import TripPlan, plan_trip

ROUTE_NAMES = {
    SHORTEST: "Shortest, ignoring flooding",
    SAFE_SHORTEST: "Shortest within your limit",
    RECOMMENDED: "Recommended",
}
SOS_UNDO_SECONDS = 5
SEARCH_INTERVAL_S = 1.0  # Nominatim usage policy: at most one request per second
COORD_DECIMALS = 6


class RequestError(ValueError):
    """A request that cannot be answered as asked (shown to the user)."""


@dataclass(frozen=True)
class Scenario:
    info: ScenarioInfo
    hazard: HazardProvider


class Service:
    def __init__(self, router: Router, resolver: PlaceResolver, refuges: RefugeIndex, scenarios: list[Scenario]):
        self.router = router
        self.graph = router.graph
        self.resolver = resolver
        self.refuges = refuges
        self.scenarios = {s.info.id: s for s in scenarios}
        crs = self.graph.graph["crs"]
        self._to_wgs = Transformer.from_crs(crs, config.WGS84, always_xy=True)
        self._to_metric = Transformer.from_crs(config.WGS84, crs, always_xy=True)
        self._search_lock = threading.Lock()
        self._last_search = 0.0
        self._cache: dict[str, object] = {}

    @classmethod
    def from_files(cls) -> Service:
        from floodroute.hazard.catalog import list_scenarios, load_hazard
        from floodroute.network import load_graph

        router = Router(load_graph(config.PROCESSED_NETWORK_PATH))
        places = config.PROCESSED_PLACES_PATH
        resolver = PlaceResolver(
            gpd.read_file(places, layer="buildings"), gpd.read_file(places, layer="entrances"), router.footpaths
        )
        graph = router.graph
        refuges = RefugeIndex(resolver, graph.graph["study_area"].buffer(graph.graph["buffer_m"]))
        return cls(router, resolver, refuges, [Scenario(info, load_hazard(info)) for info in list_scenarios()])

    # ------------------------------------------------------------------ geometry

    def to_wgs(self, geom: BaseGeometry) -> dict:
        moved = _reproject(geom, self._to_wgs)
        return _rounded(mapping(moved))

    def to_metric(self, lat: float, lon: float) -> Point:
        return Point(*self._to_metric.transform(lon, lat))

    def latlon(self, p: Point) -> dict:
        lon, lat = self._to_wgs.transform(p.x, p.y)
        return {"lat": round(lat, COORD_DECIMALS), "lon": round(lon, COORD_DECIMALS)}

    # ------------------------------------------------------------------ static data

    def area(self) -> dict:
        if "area" not in self._cache:
            area = self.graph.graph["study_area"]
            ring = area.buffer(self.graph.graph["buffer_m"])
            west, south, east, north = _reproject(ring, self._to_wgs).bounds
            self._cache["area"] = {
                "study_area": self.to_wgs(area),
                "routable_area": self.to_wgs(ring),
                "bounds": [round(v, COORD_DECIMALS) for v in (west, south, east, north)],
            }
        return self._cache["area"]

    def network(self) -> dict:
        """The walking network for display: paths inside the area, paths in the margin around it, and
        carriageways routes avoid walking along."""
        if "network" not in self._cache:
            features = []
            for *_, d in self.graph.edges(data=True):
                if not is_snappable(d):
                    continue
                if (d.get("cost_factor") or 1) > 1:
                    kind = "avoided_road"
                elif d.get("in_study_area"):
                    kind = "path"
                else:
                    kind = "margin_path"
                features.append(
                    {"type": "Feature", "properties": {"kind": kind}, "geometry": self.to_wgs(d["geometry"])}
                )
            self._cache["network"] = {"type": "FeatureCollection", "features": features}
        return self._cache["network"]

    def options(self) -> dict:
        return {
            "body_parts": [{"key": p.name.lower(), "label": p.label, "fraction": p.value} for p in BodyPart],
            "landmarks": [{"fraction": f, "name": n} for f, n in LANDMARKS],
            "dry_depth_m": DRY_DEPTH_M,
            "hard_limit_m": HARD_LIMIT_M,
            "mobility_aids": [
                {
                    "key": aid.name.lower(),
                    "label": aid.label,
                    "levels": [{"key": lv.key, "label": lv.label, "depth_m": lv.depth_m} for lv in aid.levels],
                }
                for aid in MobilityAid
                if aid is not MobilityAid.NONE
            ],
            "preferences": [
                {"key": p.name.lower(), "label": p.label, "summary": p.summary, "alpha": p.alpha}
                for p in RoutePreference
            ],
            "default_preference": DEFAULT_PREFERENCE.name.lower(),
            "flood_levels": [_level_json(level) for level in FloodLevel],
            "reference_height_m": REFERENCE_HEIGHT_M,
            "sos_undo_seconds": SOS_UNDO_SECONDS,
        }

    def scenario(self, scenario_id: str) -> Scenario:
        try:
            return self.scenarios[scenario_id]
        except KeyError:
            raise RequestError(f"Unknown flood scenario {scenario_id!r}.") from None

    def scenario_list(self) -> list[dict]:
        out = []
        for s in sorted(self.scenarios.values(), key=lambda s: s.info.order):
            typical = self._typical_depth(s.info.id)
            out.append(
                {
                    "id": s.info.id,
                    "order": s.info.order,
                    "title": s.info.title,
                    "description": s.info.description,
                    "sources": list(s.info.params.get("sources", [])),
                    "typical_depth_m": typical,
                    "level": None if typical is None else _level_json(level_of(typical)),
                }
            )
        return out

    def _typical_depth(self, scenario_id: str) -> float | None:
        key = f"typical:{scenario_id}"
        if key not in self._cache:
            snap = self.scenario(scenario_id).hazard.snapshot(self.graph)
            self._cache[key] = typical_depth_m(snap, self.graph)
        return self._cache[key]

    def water(self, scenario_id: str) -> dict:
        """Wet and unknown-depth edges of a scenario."""
        key = f"water:{scenario_id}"
        if key not in self._cache:
            snap = self.scenario(scenario_id).hazard.snapshot(self.graph)
            features = []
            for *_, d in self.graph.edges(data=True):
                c = snap.conditions.get(d["edge_id"])
                if c is None or (c.depth_m is not None and c.depth_m <= DRY_DEPTH_M):
                    continue
                features.append(
                    {
                        "type": "Feature",
                        "properties": {"depth_m": None if c.depth_m is None else round(c.depth_m, 3)},
                        "geometry": self.to_wgs(d["geometry"]),
                    }
                )
            self._cache[key] = {"type": "FeatureCollection", "features": features}
        return self._cache[key]

    # ------------------------------------------------------------------ traveller

    def traveller(
        self,
        height_cm: float,
        wading: str,
        wheelchair: bool,
        preference: str,
        alpha: float | None,
        mobility_aid: str = "none",
        aid_level: int = 0,
    ) -> dict:
        profile = make_profile(height_cm, wading, wheelchair, mobility_aid, aid_level)
        alpha = preference_alpha(preference) if alpha is None else alpha
        return {
            "depth_limit_m": profile.depth_limit_m,
            "limit_label": limit_label(profile),
            "hard_limit_m": profile.hard_limit_m,
            "mobility_aid": profile.mobility_aid.name.lower(),
            "alpha": alpha,
            "explanation": explain(alpha, profile),
        }

    # ------------------------------------------------------------------ search

    def search(self, query: str) -> list[dict]:
        query = query.strip()
        if len(query) < 3:
            return []
        return [dict(r) for r in self._search_cached(query.lower())]

    @lru_cache(maxsize=256)  # noqa: B019 - one Service per process
    def _search_cached(self, query: str) -> tuple:
        with self._search_lock:
            wait = SEARCH_INTERVAL_S - (time.monotonic() - self._last_search)
            if wait > 0:
                time.sleep(wait)
            west, south, east, north = self.area()["bounds"]
            try:
                hits = geocoding.search(query, (west, south, east, north))
            finally:
                self._last_search = time.monotonic()
        return tuple(
            (
                ("label", h.label),
                ("lat", h.lat),
                ("lon", h.lon),
                ("footprint", None if h.footprint is None else _rounded(mapping(h.footprint))),
            )
            for h in hits
        )

    # ------------------------------------------------------------------ trips

    def plan(
        self,
        start: dict,
        destination: dict,
        scenario_id: str,
        height_cm: float,
        wading: str,
        wheelchair: bool,
        preference: str,
        alpha: float | None = None,
        mobility_aid: str = "none",
        aid_level: int = 0,
    ) -> dict:
        scenario = self.scenario(scenario_id)
        profile = make_profile(height_cm, wading, wheelchair, mobility_aid, aid_level)
        alpha = preference_alpha(preference) if alpha is None else alpha
        places = {}
        for which, spec, role in (("start", start, ORIGIN), ("destination", destination, DESTINATION)):
            point = self.to_metric(spec["lat"], spec["lon"])
            if not self.router.study_area.covers(point):
                raise RequestError(f"The {which} must be inside Southbank (the black boundary on the map).")
            footprint = spec.get("footprint")
            footprint = None if footprint is None else self._footprint_metric(footprint)
            places[which] = self.resolver.resolve(point, spec.get("label") or "chosen point", footprint, role)
        snapshot = scenario.hazard.snapshot(self.graph)
        try:
            trip = plan_trip(
                self.router, self.refuges, places["start"], places["destination"], snapshot, profile, alpha
            )
        except RoutingError as exc:
            raise RequestError(str(exc)) from exc
        return self._trip_json(trip, places["start"], places["destination"], profile, alpha)

    def _footprint_metric(self, geometry: dict) -> BaseGeometry | None:
        try:
            geom = shape(geometry)
        except (KeyError, TypeError, ValueError):
            return None
        return _reproject(geom, self._to_metric)

    def _trip_json(self, trip: TripPlan, start: Place, end: Place, profile: TravellerProfile, alpha: float) -> dict:
        routes = None
        if trip.routes is not None:
            routes = {
                "alpha": alpha,
                "blocked_edges": trip.routes.blocked_edges,
                "step_free": trip.routes.step_free,
                "steps_avoided": trip.routes.steps_avoided,
                "steep_avoided": trip.routes.steep_avoided,
                "options": [
                    {
                        "kind": option.kind,
                        "name": ROUTE_NAMES[option.kind],
                        "found": option.found,
                        "error": option.error,
                        "route": None
                        if not option.found
                        else self._route_json(option.route, option.metrics, start, end),
                    }
                    for option in trip.routes.options
                ],
            }
        downgrade = None
        if trip.downgrade is not None:
            d = trip.downgrade
            downgrade = {
                "body_part": None if d.body_part is None else d.body_part.name.lower(),
                "aid_level": d.aid_level,
                "label": d.label,
                "body_part_label": d.label,
                "depth_limit_m": d.depth_limit_m,
                "required_depth_m": d.required_depth_m,
                "route": self._route_json(d.option.route, d.option.metrics, start, end),
            }
        refuge = None
        if trip.refuge is not None:
            r = trip.refuge
            refuge = {
                "name": r.refuge.name,
                "entrance_label": r.entrance_label,
                "within_limit": r.within_limit,
                "building": self.to_wgs(r.refuge.building),
                "route": self._route_json(r.route, r.metrics, start, None),
            }
        least = None
        if trip.least_water is not None:
            lw = trip.least_water
            least = {
                "required_depth_m": lw.required_depth_m,
                "required_label": profile.describe_depth(lw.required_depth_m),
                "beyond_hard_limit": lw.required_depth_m is None or lw.required_depth_m > profile.hard_limit_m,
                "deepest_point": self.latlon(lw.deepest_at),
                "route": self._route_json(lw.route, lw.metrics, start, end),
            }
        emergency = None
        if trip.emergency is not None:
            sos = trip.emergency.sos
            emergency = {
                "advice": trip.emergency.advice,
                "reason": trip.emergency.reason,
                "sos": {
                    **self.latlon(sos.location),
                    "depth_m": sos.depth_m,
                    "depth_label": sos.depth_label,
                    "level": sos.level.name.lower(),
                    "depth_limit_m": sos.depth_limit_m,
                    "created_at": sos.created_at.isoformat(),
                },
            }
        o = trip.origin
        return {
            "start": self._place_json(start),
            "destination": self._place_json(end),
            "traveller": {
                "depth_limit_m": profile.depth_limit_m,
                "limit_label": limit_label(profile),
                "height_m": profile.height_m,
                "hard_limit_m": profile.hard_limit_m,
                "mobility_aid": profile.mobility_aid.name.lower(),
                "mobility_aid_label": profile.mobility_aid.label,
            },
            "origin": {
                "level": o.level.name.lower(),
                "level_rank": int(o.level),
                "depth_m": o.depth_m,
                "depth_label": o.depth_label,
                "sheltered": o.sheltered,
                "above_knee": o.level >= AlertLevel.VERY_DEEP,
            },
            "has_safe_route": trip.has_safe_route,
            "routes": routes,
            "downgrade": downgrade,
            "refuge": refuge,
            "emergency": emergency,
            "least_water": least,
        }

    def _place_json(self, place: Place) -> dict:
        return {
            "label": place.label,
            "method": place.method,
            "point": self.latlon(place.point),
            "building": None if place.building is None else self.to_wgs(place.building),
            "access": [{**self.latlon(a.point), "label": a.label} for a in place.access],
        }

    def _route_json(self, route: Route, metrics: RouteMetrics, start: Place, end: Place | None) -> dict:
        legs = [
            LineString([route.origin.point, route.origin.snapped]),
            LineString([route.destination.snapped, route.destination.point]),
        ]
        return {
            "geometry": self.to_wgs(route.geometry),
            "access_legs": [self.to_wgs(leg) for leg in legs if leg.length > 0],
            "uses_steps": route.uses_steps,
            "max_gradient": None if route.max_gradient is None else round(route.max_gradient, 4),
            "min_gradient": None if route.min_gradient is None else round(route.min_gradient, 4),
            "from": {**self.latlon(route.origin.point), "label": start.access_label(route.origin.point)},
            "to": {
                **self.latlon(route.destination.point),
                "label": None if end is None else end.access_label(route.destination.point),
            },
            "metrics": {
                "length_m": round(metrics.length_m, 1),
                "travel_time_s": round(metrics.travel_time_s),
                "max_depth_m": metrics.max_depth_m,
                "max_depth_label": metrics.max_depth_label,
                "wading_length_m": round(metrics.wading_length_m, 1),
                "segments_over_limit": metrics.segments_over_limit,
                "detour_ratio": metrics.detour_ratio,
            },
        }


def make_profile(
    height_cm: float, wading: str, wheelchair: bool, mobility_aid: str = "none", aid_level: int = 0
) -> TravellerProfile:
    """``wheelchair=True`` without ``mobility_aid`` means a manual wheelchair, no water."""
    try:
        part = BodyPart[wading.upper()]
    except KeyError:
        raise RequestError(f"Unknown wading limit {wading!r}.") from None
    try:
        aid = MobilityAid[mobility_aid.upper()]
    except KeyError:
        raise RequestError(f"Unknown mobility aid {mobility_aid!r}.") from None
    try:
        return TravellerProfile(
            height_cm / 100, part, uses_wheelchair=wheelchair, mobility_aid=aid, aid_level=aid_level
        )
    except ValueError as exc:
        raise RequestError(str(exc)) from exc


def limit_label(profile: TravellerProfile) -> str:
    """The traveller's limit in words: a level of their device, or where it reaches on the body."""
    return profile.aid.label if profile.aid is not None else profile.describe_depth(profile.depth_limit_m)


def preference_alpha(preference: str) -> float:
    try:
        return RoutePreference[preference.upper()].alpha
    except KeyError:
        raise RequestError(f"Unknown route preference {preference!r}.") from None


def _level_json(level: FloodLevel) -> dict:
    return {
        "key": level.name.lower(),
        "label": level.label,
        "body_range": level.body_range,
        "lower_m": level.lower_m,
        "upper_m": level.upper_m,
    }


def _reproject(geom: BaseGeometry, transformer: Transformer) -> BaseGeometry:
    return shapely.transform(geom, lambda xy: np.column_stack(transformer.transform(xy[:, 0], xy[:, 1])))


def _rounded(geojson: dict) -> dict:
    def walk(c):
        if isinstance(c, (int, float)):
            return round(c, COORD_DECIMALS)
        return [walk(x) for x in c]

    if geojson["type"] == "GeometryCollection":
        return {"type": "GeometryCollection", "geometries": [_rounded(g) for g in geojson["geometries"]]}
    return {"type": geojson["type"], "coordinates": walk(geojson["coordinates"])}
