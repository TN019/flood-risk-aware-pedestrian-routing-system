"""What the web API does, independent of HTTP: load the routing data once and answer requests.

Everything leaving this module is plain JSON-ready data in WGS84 (GeoJSON geometries, coordinates
rounded to about 0.1 m), with its text in the language asked for (``api.i18n``). Everything entering
it is checked: points must lie inside the study area.
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
from floodroute.api import i18n
from floodroute.api.i18n import DEFAULT_LANGUAGE, text
from floodroute.hazard import HazardProvider
from floodroute.hazard.catalog import ScenarioInfo
from floodroute.network import is_snappable
from floodroute.places import Place, PlaceResolver
from floodroute.places.refuges import RefugeIndex
from floodroute.places.resolver import DESTINATION, ORIGIN
from floodroute.risk import DRY_DEPTH_M, HARD_LIMIT_M, BodyPart, MobilityAid, TravellerProfile
from floodroute.risk.alerts import AlertLevel
from floodroute.risk.levels import REFERENCE_HEIGHT_M, FloodLevel, level_of, typical_depth_m
from floodroute.risk.preference import DEFAULT_PREFERENCE, RoutePreference
from floodroute.risk.profile import ABOVE_SHOULDERS, DRY, LANDMARKS, UNKNOWN_DEPTH
from floodroute.routing import Route, RouteMetrics, Router, RoutingError
from floodroute.routing.planning import OVER_LIMIT
from floodroute.sources import geocoding
from floodroute.trip import TripPlan, plan_trip

SOS_UNDO_SECONDS = 5
SEARCH_INTERVAL_S = 1.0  # Nominatim usage policy: at most one request per second
COORD_DECIMALS = 6


class RequestError(ValueError):
    """A request that cannot be answered as asked (shown to the user). ``key`` and ``values`` name
    its message in the API's catalogue (``error.<key>``), so it can be shown in any language."""

    def __init__(self, key: str, **values: object):
        super().__init__(text(DEFAULT_LANGUAGE, f"error.{key}", **values))
        self.key = key
        self.values = values

    def message(self, language: str) -> str:
        return text(language, f"error.{self.key}", **self.values)

    @classmethod
    def from_routing(cls, exc: RoutingError) -> RequestError:
        return cls(exc.key or "not_connected", **exc.values)


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

    def options(self, lang: str = DEFAULT_LANGUAGE) -> dict:
        def depth(words: str) -> str:
            return text(lang, f"depth.{words.replace(' ', '_')}")

        return {
            "body_parts": [
                {"key": p.name.lower(), "label": text(lang, f"body_part.{p.name.lower()}"), "fraction": p.value}
                for p in BodyPart
            ],
            # Where water reaches on the body, to describe a depth (the map's hover text).
            "landmarks": [{"fraction": f, "key": n.replace(" ", "_"), "label": depth(n)} for f, n in LANDMARKS],
            "depth_labels": {"unknown": depth(UNKNOWN_DEPTH), "dry": depth(DRY), "above": depth(ABOVE_SHOULDERS)},
            "dry_depth_m": DRY_DEPTH_M,
            "hard_limit_m": HARD_LIMIT_M,
            "mobility_aids": [
                {
                    "key": aid.name.lower(),
                    "label": text(lang, f"mobility_aid.{aid.name.lower()}"),
                    "levels": [
                        {"key": lv.key, "label": text(lang, f"aid_level.{lv.key}"), "depth_m": lv.depth_m}
                        for lv in aid.levels
                    ],
                }
                for aid in MobilityAid
                if aid is not MobilityAid.NONE
            ],
            "preferences": [
                {
                    "key": p.name.lower(),
                    "label": text(lang, f"preference.{p.name.lower()}"),
                    "summary": text(lang, f"preference.{p.name.lower()}.summary"),
                    "alpha": p.alpha,
                }
                for p in RoutePreference
            ],
            "default_preference": DEFAULT_PREFERENCE.name.lower(),
            "flood_levels": [_level_json(level, lang) for level in FloodLevel],
            "reference_height_m": REFERENCE_HEIGHT_M,
            "sos_undo_seconds": SOS_UNDO_SECONDS,
        }

    def scenario(self, scenario_id: str) -> Scenario:
        try:
            return self.scenarios[scenario_id]
        except KeyError:
            raise RequestError("unknown_scenario", id=repr(scenario_id)) from None

    def scenario_list(self, lang: str = DEFAULT_LANGUAGE) -> list[dict]:
        """Every scenario, from normal conditions to the most severe."""
        out = []
        for s in sorted(self.scenarios.values(), key=lambda s: s.info.order):
            typical = self._typical_depth(s.info.id)
            title, description = i18n.scenario_text(lang, s.info)
            out.append(
                {
                    "id": s.info.id,
                    "order": s.info.order,
                    "title": title,
                    "description": description,
                    "sources": i18n.scenario_sources(lang, s.info),
                    "typical_depth_m": typical,
                    "level": None if typical is None else _level_json(level_of(typical), lang),
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
        lang: str = DEFAULT_LANGUAGE,
    ) -> dict:
        profile = make_profile(height_cm, wading, wheelchair, mobility_aid, aid_level)
        alpha = preference_alpha(preference) if alpha is None else alpha
        return {
            "depth_limit_m": profile.depth_limit_m,
            "limit_label": i18n.limit_label(lang, profile),
            "hard_limit_m": profile.hard_limit_m,
            "mobility_aid": profile.mobility_aid.name.lower(),
            "alpha": alpha,
            "explanation": i18n.explanation(lang, alpha, profile),
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
        lang: str = DEFAULT_LANGUAGE,
    ) -> dict:
        scenario = self.scenario(scenario_id)
        profile = make_profile(height_cm, wading, wheelchair, mobility_aid, aid_level)
        alpha = preference_alpha(preference) if alpha is None else alpha
        places = {}
        for which, spec, role in (("start", start, ORIGIN), ("destination", destination, DESTINATION)):
            point = self.to_metric(spec["lat"], spec["lon"])
            if not self.router.study_area.covers(point):
                raise RequestError(f"{which}_outside_area")
            footprint = spec.get("footprint")
            footprint = None if footprint is None else self._footprint_metric(footprint)
            label = spec.get("label") or text(lang, "place.chosen_point")
            places[which] = self.resolver.resolve(point, label, footprint, role)
        snapshot = scenario.hazard.snapshot(self.graph)
        try:
            trip = plan_trip(
                self.router, self.refuges, places["start"], places["destination"], snapshot, profile, alpha
            )
        except RoutingError as exc:
            raise RequestError.from_routing(exc) from exc
        return self._trip_json(trip, places["start"], places["destination"], profile, alpha, lang)

    def _footprint_metric(self, geometry: dict) -> BaseGeometry | None:
        try:
            geom = shape(geometry)
        except (KeyError, TypeError, ValueError):
            return None
        return _reproject(geom, self._to_metric)

    def _trip_json(
        self, trip: TripPlan, start: Place, end: Place, profile: TravellerProfile, alpha: float, lang: str
    ) -> dict:
        def depth(depth_m: float | None) -> str:
            return i18n.depth_label(lang, depth_m, profile.height_m)

        def route(r: Route, metrics: RouteMetrics, to: Place | None) -> dict:
            return self._route_json(r, metrics, start, to, profile, lang)

        routes = None
        if trip.routes is not None:
            plan = trip.routes
            routes = {
                "alpha": alpha,
                "blocked_edges": plan.blocked_edges,
                "step_free": plan.step_free,
                "steps_avoided": plan.steps_avoided,
                "steep_avoided": plan.steep_avoided,
                "options": [
                    {
                        "kind": option.kind,
                        "name": text(lang, f"route.{option.kind}"),
                        "found": option.found,
                        "error": None if option.found else _route_error(option.reason, plan.step_free, profile, lang),
                        "route": None if not option.found else route(option.route, option.metrics, end),
                    }
                    for option in plan.options
                ],
            }
        downgrade = None
        if trip.downgrade is not None:
            d = trip.downgrade
            if d.body_part is not None:
                key = d.body_part.name.lower()
                label = text(lang, f"body_part.{key}")
            else:
                key = profile.mobility_aid.levels[d.aid_level].key
                label = text(lang, f"aid_level.{key}")
            downgrade = {
                "body_part": None if d.body_part is None else d.body_part.name.lower(),
                "aid_level": d.aid_level,
                "label": label,
                "body_part_label": label,
                "water": text(lang, f"water.{key}"),  # the water the higher limit accepts, in words
                "depth_limit_m": d.depth_limit_m,
                "required_depth_m": d.required_depth_m,
                "route": route(d.option.route, d.option.metrics, end),
            }
        refuge = None
        if trip.refuge is not None:
            r = trip.refuge
            refuge = {
                "name": r.refuge.name if r.refuge.named else text(lang, "place.building"),
                "entrance_label": i18n.access_label(lang, r.entrance),
                "within_limit": r.within_limit,
                "building": self.to_wgs(r.refuge.building),
                "route": route(r.route, r.metrics, None),
            }
        least = None
        if trip.least_water is not None:
            lw = trip.least_water
            least = {
                "required_depth_m": lw.required_depth_m,
                "required_label": depth(lw.required_depth_m),
                "beyond_hard_limit": lw.required_depth_m is None or lw.required_depth_m > profile.hard_limit_m,
                "deepest_point": self.latlon(lw.deepest_at),
                "route": route(lw.route, lw.metrics, end),
            }
        o = trip.origin
        origin_label = text(lang, "depth.indoors") if o.sheltered else depth(o.depth_m)
        emergency = None
        if trip.emergency is not None:
            sos = trip.emergency.sos
            emergency = {
                "advice": trip.emergency.advice,
                "reason": trip.emergency.reason,
                "sos": {
                    **self.latlon(sos.location),
                    "depth_m": sos.depth_m,
                    "depth_label": origin_label,
                    "level": sos.level.name.lower(),
                    "depth_limit_m": sos.depth_limit_m,
                    "created_at": sos.created_at.isoformat(),
                },
            }
        return {
            "start": self._place_json(start, lang),
            "destination": self._place_json(end, lang),
            "traveller": {
                "depth_limit_m": profile.depth_limit_m,
                "limit_label": i18n.limit_label(lang, profile),
                "height_m": profile.height_m,
                "hard_limit_m": profile.hard_limit_m,
                "mobility_aid": profile.mobility_aid.name.lower(),
                "mobility_aid_label": text(lang, f"mobility_aid.{profile.mobility_aid.name.lower()}"),
            },
            "origin": {
                "level": o.level.name.lower(),
                "level_rank": int(o.level),
                "depth_m": o.depth_m,
                "depth_label": origin_label,
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

    def _place_json(self, place: Place, lang: str) -> dict:
        return {
            "label": place.label,
            "method": place.method,
            "point": self.latlon(place.point),
            "building": None if place.building is None else self.to_wgs(place.building),
            "access": [{**self.latlon(a.point), "label": i18n.access_label(lang, a)} for a in place.access],
        }

    def _route_json(
        self,
        route: Route,
        metrics: RouteMetrics,
        start: Place,
        end: Place | None,
        profile: TravellerProfile,
        lang: str,
    ) -> dict:
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
            "from": {
                **self.latlon(route.origin.point),
                "label": i18n.access_label(lang, start.access_at(route.origin.point)),
            },
            "to": {
                **self.latlon(route.destination.point),
                "label": None if end is None else i18n.access_label(lang, end.access_at(route.destination.point)),
            },
            "metrics": {
                "length_m": round(metrics.length_m, 1),
                "travel_time_s": round(metrics.travel_time_s),
                "max_depth_m": metrics.max_depth_m,
                "max_depth_label": i18n.depth_label(lang, metrics.max_depth_m, profile.height_m),
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
        raise RequestError("unknown_wading", value=repr(wading)) from None
    try:
        aid = MobilityAid[mobility_aid.upper()]
    except KeyError:
        raise RequestError("unknown_mobility_aid", value=repr(mobility_aid)) from None
    device = MobilityAid.MANUAL_WHEELCHAIR if wheelchair and aid is MobilityAid.NONE else aid
    if device is not MobilityAid.NONE and not 0 <= aid_level < len(device.levels):
        raise RequestError("no_aid_level", level=aid_level)
    try:
        return TravellerProfile(
            height_cm / 100, part, uses_wheelchair=wheelchair, mobility_aid=aid, aid_level=aid_level
        )
    except ValueError as exc:
        raise RequestError("invalid_traveller") from exc


def preference_alpha(preference: str) -> float:
    try:
        return RoutePreference[preference.upper()].alpha
    except KeyError:
        raise RequestError("unknown_preference", value=repr(preference)) from None


def _route_error(reason: str | None, step_free: bool, profile: TravellerProfile, lang: str) -> str:
    """Why an option has no route."""
    if reason == OVER_LIMIT:
        key = "over_limit_step_free" if step_free else "over_limit"
        return text(lang, f"route_error.{key}", limit=f"{profile.depth_limit_m * 100:.0f}")
    return text(lang, "route_error.no_step_free_route")


def _level_json(level: FloodLevel, lang: str = DEFAULT_LANGUAGE) -> dict:
    key = level.name.lower()
    return {
        "key": key,
        "label": text(lang, f"flood_level.{key}"),
        "body_range": text(lang, f"flood_level.{key}.range"),
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
