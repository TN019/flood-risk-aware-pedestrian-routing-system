"""Verification harness: run cases A–J and compare with the predictions in docs/verification.md.

Part 1 builds the small "test town" from that document, where every expected number was worked out
by hand, and checks the program's results against those numbers. Part 2 checks properties that
must hold for every trip on the Southbank network. ``scripts/verify.py`` writes the comparison
report; ``tests/test_verification.py`` runs the same checks.

The predicted values below are copied from docs/verification.md, which was written and committed
before this harness was run.
"""

from __future__ import annotations

import itertools
import random
from collections.abc import Callable
from dataclasses import dataclass

import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, Point, box

from floodroute import config
from floodroute.hazard import DRY, EdgeCondition, HazardSnapshot
from floodroute.places import PlaceResolver
from floodroute.places.refuges import RefugeIndex
from floodroute.risk import BodyPart, DepthRelativeRisk, MobilityAid, TravellerProfile, risk_cost
from floodroute.risk.alerts import AlertLevel
from floodroute.risk.model import source_edge_id
from floodroute.routing import Route, Router, RoutingError, plan_routes
from floodroute.trip import ONLY_OPTION, plan_trip

LENGTH_TOL_M = 0.01
ADULT, CHILD, TALL = 1.70, 1.20, 1.90
STEEPEST_RAMP = 1 / 14  # AS 1428.1; the limit the predictions in case J and R-I were derived with


@dataclass(frozen=True)
class Check:
    case: str
    item: str
    predicted: object
    actual: object
    informational: bool = False  # recorded for the report, not a prediction

    @property
    def ok(self) -> bool:
        if self.informational:
            return True
        p, a = self.predicted, self.actual
        if isinstance(p, float) and isinstance(a, (int, float)):
            return abs(p - a) <= LENGTH_TOL_M
        return p == a


# ---------------------------------------------------------------------------------------------- test town

NODES = {
    "B0": (0, 0),
    "B1": (100, 0),
    "B2": (200, 0),
    "B3": (300, 0),
    "T0": (0, 50),
    "T1": (100, 50),
    "T2": (200, 50),
    "T3": (300, 50),
}
EDGES = {
    "b01": ("B0", "B1"),
    "b12": ("B1", "B2"),
    "b23": ("B2", "B3"),
    "t01": ("T0", "T1"),
    "t12": ("T1", "T2"),
    "t23": ("T2", "T3"),
    "c0": ("B0", "T0"),
    "c1": ("B1", "T1"),
    "c2": ("B2", "T2"),
    "c3": ("B3", "T3"),
}
SHELTER = box(-40, 10, -10, 40)
SHELTER_DOOR = (-10, 25)
START, END = Point(0, 0), Point(300, 0)


def test_town(
    with_shelter: bool = True, steps: tuple[str, ...] = (), gradients: dict[str, float | None] | None = None
) -> tuple[Router, PlaceResolver, RefugeIndex]:
    gradients = gradients or {}
    g = nx.Graph(crs=config.METRIC_CRS)
    for n, (x, y) in NODES.items():
        g.add_node(n, x=x, y=y, kind="junction", in_study_area=True)
    for eid, (u, v) in EDGES.items():
        geom = LineString([NODES[u], NODES[v]])
        g.add_edge(
            u,
            v,
            geometry=geom,
            length_m=geom.length,
            edge_id=eid,
            cost_factor=1.0,
            in_study_area=True,
            is_steps=eid in steps,
            gradient=gradients.get(eid),
        )
    router = Router(g)
    names, shapes, doors = (["Shelter"], [SHELTER], [SHELTER_DOOR]) if with_shelter else ([], [], [(9e5, 9e5)])
    buildings = gpd.GeoDataFrame({"name": names, "geometry": shapes}, geometry="geometry", crs=config.METRIC_CRS)
    entrances = gpd.GeoDataFrame(
        {"element": "node", "id": range(len(doors)), "entrance": "main", "geometry": [Point(d) for d in doors]},
        geometry="geometry",
        crs=config.METRIC_CRS,
    )
    resolver = PlaceResolver(buildings, entrances, router.footpaths)
    return router, resolver, RefugeIndex(resolver)


def flood(**depths: float | None) -> HazardSnapshot:
    return HazardSnapshot("test", conditions={e: EdgeCondition(d) for e, d in depths.items()}, default=DRY)


def adult(part: BodyPart = BodyPart.ANKLE, **kw) -> TravellerProfile:
    return TravellerProfile(ADULT, part, **kw)


def _trip(snapshot, profile, alpha=2.0, start=START, end=END, with_shelter=True, steps=(), gradients=None):
    router, resolver, refuges = test_town(with_shelter, steps, gradients)
    o = resolver.resolve(start, "start", role="origin")
    d = resolver.resolve(end, "end")
    return plan_trip(router, refuges, o, d, snapshot, profile, alpha)


def _len(option) -> float | None:
    return round(option.route.length_m, 3) if option.found else None


def run_test_town() -> list[Check]:
    checks: list[Check] = []
    add = lambda case, item, predicted, actual: checks.append(Check(case, item, predicted, actual))  # noqa: E731

    # A — normal conditions
    t = _trip(flood(), adult())
    r = t.routes
    add("A", "shortest / within limit / recommended (m)", (300.0, 300.0, 300.0), tuple(map(_len, r.options)))
    add(
        "A",
        "all three are the same route",
        True,
        r.shortest.route.geometry.equals(r.recommended.route.geometry)
        and r.safe_shortest.route.geometry.equals(r.recommended.route.geometry),
    )
    add("A", "travel time (s)", 230.769, round(r.recommended.metrics.travel_time_s, 3))
    add("A", "deepest water (m)", 0.0, r.recommended.metrics.max_depth_m)
    add("A", "edges over the limit", 0, r.blocked_edges)
    add("A", "downgrade / refuge / emergency", (None, None, None), (t.downgrade, t.refuge, t.emergency))

    # B — unsafe edge excluded
    t = _trip(flood(b12=0.10), adult())
    s = t.routes.shortest
    add("B", "shortest ignoring flooding (m)", 300.0, _len(s))
    add(
        "B",
        "its deepest water and body label",
        (0.10, "up to the lower calf"),
        (s.metrics.max_depth_m, s.metrics.max_depth_label),
    )
    add("B", "its distance in water (m)", 100.0, round(s.metrics.wading_length_m, 3))
    add("B", "its sections over the limit", 1, s.metrics.segments_over_limit)
    add("B", "shortest within limit (m)", 400.0, _len(t.routes.safe_shortest))
    for alpha in (0.0, 2.0, 10.0):
        rt = _trip(flood(b12=0.10), adult(), alpha=alpha).routes.recommended
        add(
            "B",
            f"recommended with α = {alpha:g} (m), water (m)",
            (400.0, 0.0),
            (_len(rt), round(rt.metrics.wading_length_m, 3)),
        )
    add("B", "edges over the limit", 1, t.routes.blocked_edges)

    # C — lower-risk detour (adult, mid calf)
    mid = adult(BodyPart.MID_CALF)
    t = _trip(flood(b12=0.20), mid)
    add(
        "C1",
        "recommended (m), water (m)",
        (400.0, 0.0),
        (_len(t.routes.recommended), round(t.routes.recommended.metrics.wading_length_m, 3)),
    )
    add(
        "C1",
        "shortest within limit (m), water (m)",
        (300.0, 100.0),
        (_len(t.routes.safe_shortest), round(t.routes.safe_shortest.metrics.wading_length_m, 3)),
    )
    t = _trip(flood(b12=0.10), mid)
    add(
        "C2",
        "recommended (m), water (m)",
        (300.0, 100.0),
        (_len(t.routes.recommended), round(t.routes.recommended.metrics.wading_length_m, 3)),
    )
    add("C3", "recommended with α = 1.3 (m)", 300.0, _len(_trip(flood(b12=0.20), mid, alpha=1.3).routes.recommended))
    add("C4", "recommended with α = 1.5 (m)", 400.0, _len(_trip(flood(b12=0.20), mid, alpha=1.5).routes.recommended))

    # D — different travellers, b12 at 10 cm
    for label, profile, predicted in (
        ("adult, mid calf", adult(BodyPart.MID_CALF), 300.0),
        ("adult, lower calf", adult(BodyPart.LOWER_CALF), 300.0),
        ("adult, ankle", adult(BodyPart.ANKLE), 400.0),
        ("child, mid calf", TravellerProfile(CHILD, BodyPart.MID_CALF), 400.0),
        ("child, lower calf", TravellerProfile(CHILD, BodyPart.LOWER_CALF), 400.0),
        ("wheelchair", adult(BodyPart.MID_CALF, uses_wheelchair=True), 400.0),
    ):
        add("D", f"recommended for {label} (m)", predicted, _len(_trip(flood(b12=0.10), profile).routes.recommended))

    # E — no route within the limit
    t = _trip(flood(b12=0.40, t12=0.40), mid)
    s = t.routes.shortest
    add("E1", "route within limit", False, t.has_safe_route)
    add(
        "E1",
        "shortest ignoring flooding (m), deepest, label",
        (300.0, 0.40, "up to the knee"),
        (_len(s), s.metrics.max_depth_m, s.metrics.max_depth_label),
    )
    d = t.downgrade
    add(
        "E1",
        "downgrade to, least water (m), route (m)",
        ("knee", 0.40, 300.0),
        (d.body_part.label, d.required_depth_m, round(d.option.route.length_m, 3)) if d else None,
    )
    add(
        "E1",
        "refuge, length (m), within limit",
        ("Shelter", 35.0, True),
        (t.refuge.refuge.name, round(t.refuge.route.length_m, 3), t.refuge.within_limit) if t.refuge else None,
    )
    add("E1", "start level, emergency", ("OK", None), (t.origin.level.name, t.emergency))

    t = _trip(flood(b12=0.15, t12=0.25), adult())
    d = t.downgrade
    add("E2", "route within limit", False, t.has_safe_route)
    add(
        "E2",
        "downgrade to, least water (m), route (m)",
        ("lower calf", 0.15, 300.0),
        (d.body_part.label, d.required_depth_m, round(d.option.route.length_m, 3)) if d else None,
    )
    add(
        "E2",
        "refuge, length (m), within limit",
        ("Shelter", 35.0, True),
        (t.refuge.refuge.name, round(t.refuge.route.length_m, 3), t.refuge.within_limit) if t.refuge else None,
    )
    add("E2", "emergency", None, t.emergency)

    standing = Point(150, 0)
    t = _trip(flood(b12=0.40, t12=0.40), mid, start=standing)
    add("E3", "start depth (m), level", (0.40, "OVER_LIMIT"), (t.origin.depth_m, t.origin.level.name))
    add("E3", "emergency", None, t.emergency)
    d = t.downgrade
    add(
        "E3",
        "downgrade to, least water (m), route (m)",
        ("knee", 0.40, 150.0),
        (d.body_part.label, d.required_depth_m, round(d.option.route.length_m, 3)) if d else None,
    )
    add(
        "E3",
        "refuge, length (m), deepest (m), within limit",
        ("Shelter", 185.0, 0.40, False),
        (t.refuge.refuge.name, round(t.refuge.route.length_m, 3), t.refuge.metrics.max_depth_m, t.refuge.within_limit)
        if t.refuge
        else None,
    )
    t = _trip(flood(b12=0.90, t12=0.90), mid, start=standing)
    add(
        "E4",
        "level, emergency advice",
        ("CRITICAL", "strongly recommended"),
        (t.origin.level.name, t.emergency.advice if t.emergency else None),
    )
    t = _trip(flood(b12=0.40, t12=0.40), TravellerProfile(CHILD, BodyPart.MID_CALF), start=standing)
    add(
        "E5",
        "level, emergency advice",
        ("VERY_DEEP", "recommended"),
        (t.origin.level.name, t.emergency.advice if t.emergency else None),
    )
    t = _trip(flood(b12=0.40, t12=0.40), mid, with_shelter=False)
    add("E6", "refuge, emergency advice", (None, ONLY_OPTION), (t.refuge, t.emergency.advice if t.emergency else None))
    t = _trip(flood(b12=0.60, t12=0.60), mid)
    add("E7", "route within limit", False, t.has_safe_route)
    add("E7", "downgrade", None, t.downgrade)
    add(
        "E7",
        "refuge, length (m), within limit",
        ("Shelter", 35.0, True),
        (t.refuge.refuge.name, round(t.refuge.route.length_m, 3), t.refuge.within_limit) if t.refuge else None,
    )
    add("E7", "start level, emergency", ("OK", None), (t.origin.level.name, t.emergency))
    t = _trip(flood(b12=0.52, t12=0.52), TravellerProfile(TALL, BodyPart.MID_CALF), start=standing)
    add("E8", "start depth (m), level", (0.52, "DEEP"), (t.origin.depth_m, t.origin.level.name))
    add(
        "E8",
        "emergency advice, SOS depth (m)",
        ("available", 0.52),
        (t.emergency.advice, t.emergency.sos.depth_m) if t.emergency else None,
    )
    add("E8", "downgrade", None, t.downgrade)
    add(
        "E8",
        "refuge, length (m), deepest (m), within limit",
        ("Shelter", 185.0, 0.52, False),
        (t.refuge.refuge.name, round(t.refuge.route.length_m, 3), t.refuge.metrics.max_depth_m, t.refuge.within_limit)
        if t.refuge
        else None,
    )

    # F — switching conditions on one router
    router, resolver, refuges = test_town()
    o, d = resolver.resolve(START, "start", role="origin"), resolver.resolve(END, "end")
    seq = [plan_trip(router, refuges, o, d, s, adult()) for s in (flood(), flood(b12=0.10), flood())]
    add(
        "F",
        "recommended normal → flooded → normal (m)",
        (300.0, 400.0, 300.0),
        tuple(_len(p.routes.recommended) for p in seq),
    )
    add("F", "edges over the limit", (0, 1, 0), tuple(p.routes.blocked_edges for p in seq))

    # G — steps and wheelchair users
    wheelchair = adult(BodyPart.MID_CALF, uses_wheelchair=True)
    t = _trip(flood(), adult(), steps=("b12",))
    r = t.routes
    add("G1", "adult: shortest / within limit / recommended (m)", (300.0, 300.0, 300.0), tuple(map(_len, r.options)))
    add("G1", "adult: every route through b12, steps avoided", (True, False), (_all_use(r, "b12"), r.steps_avoided))
    t = _trip(flood(), wheelchair, steps=("b12",))
    r = t.routes
    add(
        "G1",
        "wheelchair: shortest / within limit / recommended (m)",
        (400.0, 400.0, 400.0),
        tuple(map(_len, r.options)),
    )
    add(
        "G1",
        "wheelchair: any route through b12, steps avoided",
        (False, True),
        (any("b12" in _sources(o) for o in r.options), r.steps_avoided),
    )
    add("G1", "wheelchair: edges over the limit", 0, r.blocked_edges)

    t = _trip(flood(t12=0.10), adult(), steps=("b12",))
    add("G2", "adult: recommended (m)", 300.0, _len(t.routes.recommended))
    t = _trip(flood(t12=0.10), wheelchair, steps=("b12",))
    lw = t.least_water
    add("G2", "wheelchair: route within limit", False, t.has_safe_route)
    add("G2", "wheelchair: shortest ignoring flooding (m)", 400.0, _len(t.routes.shortest))
    add(
        "G2",
        "wheelchair: least water (m), its route (m)",
        (0.10, 400.0),
        (lw.required_depth_m, round(lw.route.length_m, 3)) if lw else None,
    )
    add("G2", "wheelchair: downgrade", None, t.downgrade)
    add(
        "G2",
        "wheelchair: refuge, length (m), within limit",
        ("Shelter", 35.0, True),
        (t.refuge.refuge.name, round(t.refuge.route.length_m, 3), t.refuge.within_limit) if t.refuge else None,
    )
    add("G2", "wheelchair: start level, emergency", ("OK", None), (t.origin.level.name, t.emergency))

    t = _trip(flood(b12=0.10, t12=0.10), adult(), steps=("c0",))
    d = t.downgrade
    add("G3", "adult: route within limit", False, t.has_safe_route)
    add(
        "G3",
        "adult: downgrade to, least water (m), route (m)",
        ("lower calf", 0.10, 300.0),
        (d.body_part.label, d.required_depth_m, round(d.option.route.length_m, 3)) if d else None,
    )
    add(
        "G3",
        "adult: refuge, length (m), within limit",
        ("Shelter", 35.0, True),
        (t.refuge.refuge.name, round(t.refuge.route.length_m, 3), t.refuge.within_limit) if t.refuge else None,
    )
    add("G3", "adult: emergency", None, t.emergency)
    t = _trip(flood(b12=0.10, t12=0.10), wheelchair, steps=("c0",))
    lw = t.least_water
    add("G3", "wheelchair: route within limit", False, t.has_safe_route)
    add(
        "G3",
        "wheelchair: least water (m), its route (m)",
        (0.10, 300.0),
        (lw.required_depth_m, round(lw.route.length_m, 3)) if lw else None,
    )
    add("G3", "wheelchair: downgrade, refuge", (None, None), (t.downgrade, t.refuge))
    add("G3", "wheelchair: emergency advice", ONLY_OPTION, t.emergency.advice if t.emergency else None)

    # H — mobility aids and their levels
    def aid(device: MobilityAid, level: int = 0) -> TravellerProfile:
        return TravellerProfile(ADULT, mobility_aid=device, aid_level=level)

    manual, powered, scooter = (
        MobilityAid.MANUAL_WHEELCHAIR,
        MobilityAid.POWERED_WHEELCHAIR,
        MobilityAid.MOBILITY_SCOOTER,
    )

    def downgrade(t) -> tuple | None:
        d = t.downgrade
        return (d.label, d.required_depth_m, round(d.option.route.length_m, 3)) if d else None

    def refuge(t) -> tuple | None:
        r = t.refuge
        return (r.refuge.name, round(r.route.length_m, 3), r.within_limit) if r else None

    t = _trip(flood(b12=0.04), aid(manual))
    add(
        "H1",
        "manual, no water: within limit / recommended (m)",
        (400.0, 400.0),
        (_len(t.routes.safe_shortest), _len(t.routes.recommended)),
    )
    t = _trip(flood(b12=0.04), aid(manual, 1))
    add(
        "H2",
        "manual, 5 cm: within limit / recommended (m)",
        (300.0, 400.0),
        (_len(t.routes.safe_shortest), _len(t.routes.recommended)),
    )
    add(
        "H2", "manual, 5 cm: deepest on the shortest within limit (m)", 0.04, t.routes.safe_shortest.metrics.max_depth_m
    )
    t = _trip(flood(b12=0.04), aid(scooter, 1))
    add("H3", "scooter, 2.5 cm: recommended (m)", 400.0, _len(t.routes.recommended))

    t = _trip(flood(b12=0.04, t12=0.04), aid(manual))
    lw = t.least_water
    add("H4", "manual, no water: route within limit", False, t.has_safe_route)
    add(
        "H4",
        "manual: least water (m), its route (m)",
        (0.04, 300.0),
        (lw.required_depth_m, round(lw.route.length_m, 3)) if lw else None,
    )
    add(
        "H4",
        "manual: downgrade to, least water (m), route (m)",
        ("below a 4-inch castor axle", 0.04, 300.0),
        downgrade(t),
    )
    add("H4", "manual: refuge, length (m), within limit", ("Shelter", 35.0, True), refuge(t))
    add("H4", "manual: emergency", None, t.emergency)
    t = _trip(flood(b12=0.04, t12=0.04), aid(scooter))
    add("H5", "scooter, no water: route within limit", False, t.has_safe_route)
    add("H5", "scooter: least water (m)", 0.04, t.least_water.required_depth_m if t.least_water else None)
    add("H5", "scooter: downgrade", None, t.downgrade)
    add("H5", "scooter: refuge, length (m), within limit", ("Shelter", 35.0, True), refuge(t))

    t = _trip(flood(b12=0.07, t12=0.07), aid(powered))
    add("H6", "powered, no water: downgrade", None, t.downgrade)
    t = _trip(flood(b12=0.07, t12=0.07), aid(manual))
    add(
        "H6",
        "manual, no water: downgrade to, least water (m), route (m)",
        ("below a 6-inch castor axle", 0.07, 300.0),
        downgrade(t),
    )

    # I — cut off inside a building
    inside = Point(-25, 25)

    def emergency(t) -> tuple | None:
        return (t.emergency.advice, t.emergency.reason) if t.emergency else None

    def least(t) -> tuple | None:
        lw = t.least_water
        return (lw.required_depth_m, round(lw.route.length_m, 3)) if lw else None

    t = _trip(flood(), adult(), start=inside)
    add("I1", "sheltered, recommended (m)", (True, 335.0), (t.origin.sheltered, _len(t.routes.recommended)))
    add("I1", "emergency", None, t.emergency)
    t = _trip(flood(b12=0.60, t12=0.60), adult(BodyPart.MID_CALF), start=inside)
    add("I2", "route within limit", False, t.has_safe_route)
    add("I2", "least water (m), its route (m)", (0.60, 335.0), least(t))
    add("I2", "downgrade, refuge", (None, None), (t.downgrade, t.refuge))
    add("I2", "emergency advice, reason", ("available", "cut_off"), emergency(t))
    t = _trip(flood(b12=0.40, t12=0.40), adult(BodyPart.MID_CALF), start=inside)
    add("I3", "least water (m)", 0.40, t.least_water.required_depth_m if t.least_water else None)
    add("I3", "downgrade to, least water (m), route (m)", ("knee", 0.40, 335.0), downgrade(t))
    add("I3", "emergency", None, t.emergency)
    t = _trip(flood(b12=None, t12=None), adult(), start=inside)
    lw = t.least_water
    add("I4", "least water (m), downgrade", (None, None), (lw.required_depth_m if lw else "none", t.downgrade))
    add("I4", "emergency advice, reason", ("available", "cut_off"), emergency(t))
    t = _trip(flood(b12=0.60, t12=0.60), adult(BodyPart.MID_CALF))
    add(
        "I5",
        "sheltered, start level, downgrade",
        (False, AlertLevel.OK, None),
        (t.origin.sheltered, t.origin.level, t.downgrade),
    )
    add("I5", "refuge, length (m), within limit", ("Shelter", 35.0, True), refuge(t))
    add("I5", "emergency", None, t.emergency)
    t = _trip(flood(b12=0.10, t12=0.10), aid(manual), start=inside)
    add("I6", "least water (m), its route (m)", (0.10, 335.0), least(t))
    add("I6", "downgrade", None, t.downgrade)
    add("I6", "emergency advice, reason", ("available", "cut_off"), emergency(t))

    # J — steep paths and mobility aid users
    steep = {"b12": 1 / 10}
    t = _trip(flood(), adult(), gradients=steep)
    r = t.routes
    add("J1", "adult: shortest / within limit / recommended (m)", (300.0, 300.0, 300.0), tuple(map(_len, r.options)))
    add("J1", "adult: every route through b12, steep avoided", (True, False), (_all_use(r, "b12"), _steep_avoided(r)))
    t = _trip(flood(), aid(manual), gradients=steep)
    r = t.routes
    add(
        "J1",
        "manual: shortest / within limit / recommended (m)",
        (400.0, 400.0, 400.0),
        tuple(map(_len, r.options)),
    )
    add(
        "J1",
        "manual: any route through b12, steep avoided, steps avoided",
        (False, True, False),
        (any("b12" in _sources(o) for o in r.options), _steep_avoided(r), r.steps_avoided),
    )
    add("J1", "manual: edges over the limit", 0, r.blocked_edges)
    add(
        "J1",
        "powered / scooter: recommended (m)",
        (400.0, 400.0),
        tuple(_len(_trip(flood(), aid(device), gradients=steep).routes.recommended) for device in (powered, scooter)),
    )

    add(
        "J2",
        "manual: recommended at 1:14 / 1:13 / no gradient (m)",
        (300.0, 400.0, 300.0),
        tuple(
            _len(_trip(flood(), aid(manual), gradients={"b12": g}).routes.recommended)
            for g in (STEEPEST_RAMP, 1 / 13, None)
        ),
    )

    t = _trip(flood(t12=0.04), adult(), gradients=steep)
    add("J3", "adult: recommended (m)", 300.0, _len(t.routes.recommended))
    t = _trip(flood(t12=0.04), aid(powered), gradients=steep)
    add("J3", "powered: route within limit", False, t.has_safe_route)
    add(
        "J3",
        "powered: shortest ignoring flooding (m), steep avoided",
        (400.0, True),
        (_len(t.routes.shortest), _steep_avoided(t.routes)),
    )
    add("J3", "powered: least water (m), its route (m)", (0.04, 400.0), least(t))
    add(
        "J3",
        "powered: downgrade to, least water (m), route (m)",
        ("well below the chassis", 0.04, 400.0),
        downgrade(t),
    )
    add("J3", "powered: refuge, length (m), within limit", ("Shelter", 35.0, True), refuge(t))
    add("J3", "powered: emergency", None, t.emergency)
    t = _trip(flood(t12=0.04), aid(scooter), gradients=steep)
    add("J3", "scooter: route within limit", False, t.has_safe_route)
    add("J3", "scooter: least water (m)", 0.04, t.least_water.required_depth_m if t.least_water else None)
    add("J3", "scooter: downgrade", None, t.downgrade)
    add("J3", "scooter: refuge, length (m), within limit", ("Shelter", 35.0, True), refuge(t))

    steep_c0 = {"c0": 1 / 10}
    t = _trip(flood(b12=0.10, t12=0.10), adult(), gradients=steep_c0)
    add("J4", "adult: route within limit", False, t.has_safe_route)
    add("J4", "adult: downgrade to, least water (m), route (m)", ("lower calf", 0.10, 300.0), downgrade(t))
    add("J4", "adult: refuge, length (m), within limit", ("Shelter", 35.0, True), refuge(t))
    add("J4", "adult: emergency", None, t.emergency)
    t = _trip(flood(b12=0.10, t12=0.10), aid(manual), gradients=steep_c0)
    add("J4", "manual: route within limit", False, t.has_safe_route)
    add("J4", "manual: least water (m), its route (m)", (0.10, 300.0), least(t))
    add("J4", "manual: downgrade, refuge", (None, None), (t.downgrade, t.refuge))
    add("J4", "manual: emergency advice", ONLY_OPTION, t.emergency.advice if t.emergency else None)
    return checks


def _steep_avoided(plan) -> bool | None:
    return getattr(plan, "steep_avoided", None)


def _sources(option) -> set[str]:
    return {s.source_edge_id for s in option.route.segments} if option.found else set()


def _all_use(plan, edge_id: str) -> bool:
    return all(edge_id in _sources(o) for o in plan.options)


# ---------------------------------------------------------------------------------------------- Southbank


def route_cost(route: Route, graph: nx.Graph, cost: Callable) -> float | None:
    """Total ``cost`` of an already planned route, rebuilt from its segments."""
    factor = {d["edge_id"]: d.get("cost_factor") or 1.0 for *_, d in graph.edges(data=True)}
    total = 0.0
    for seg in route.segments:
        data = {
            "edge_id": seg.source_edge_id,
            "length_m": seg.length_m,
            "parent_length_m": seg.source_length_m,
            "cost_factor": 1.0 if seg.is_access else factor[seg.source_edge_id],
            "standing_on": seg.standing_on,
        }
        c = cost(None, None, data)
        if c is None:
            return None
        total += c
    return total


def run_southbank(trips: int = 100, seed: int = 2026) -> list[Check]:
    from floodroute.hazard.catalog import list_scenarios, load_hazard
    from floodroute.network import load_graph

    g = load_graph(config.PROCESSED_NETWORK_PATH)
    router = Router(g)
    places = config.PROCESSED_PLACES_PATH
    resolver = PlaceResolver(
        gpd.read_file(places, layer="buildings"), gpd.read_file(places, layer="entrances"), router.footpaths
    )
    refuges = RefugeIndex(resolver, g.graph["study_area"].buffer(g.graph["buffer_m"]))
    area = g.graph["study_area"]
    minx, miny, maxx, maxy = area.bounds
    rng = random.Random(seed)
    pairs = []
    while len(pairs) < trips:
        a, b = (Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy)) for _ in range(2))
        if area.contains(a) and area.contains(b):
            try:
                router.route(a, b)
            except RoutingError:
                continue
            pairs.append((resolver.resolve(a, "a", role="origin"), resolver.resolve(b, "b")))
    parts = [BodyPart.NO_WADING, BodyPart.ANKLE, BodyPart.LOWER_CALF, BodyPart.MID_CALF, BodyPart.KNEE]
    travellers = {p.label: adult(p) for p in parts}
    travellers["child, ankle"] = TravellerProfile(CHILD, BodyPart.ANKLE)
    travellers["wheelchair"] = adult(BodyPart.MID_CALF, uses_wheelchair=True)  # manual wheelchair, no water
    manual_levels = ["wheelchair", "manual wheelchair, 5 cm", "manual wheelchair, 7.5 cm"]
    travellers[manual_levels[1]] = TravellerProfile(ADULT, mobility_aid=MobilityAid.MANUAL_WHEELCHAIR, aid_level=1)
    travellers[manual_levels[2]] = TravellerProfile(ADULT, mobility_aid=MobilityAid.MANUAL_WHEELCHAIR, aid_level=2)
    travellers["mobility scooter, 2.5 cm"] = TravellerProfile(
        ADULT, mobility_aid=MobilityAid.MOBILITY_SCOOTER, aid_level=1
    )
    model = DepthRelativeRisk()
    steep = {d["edge_id"] for *_, d in g.edges(data=True) if (d.get("gradient") or 0) > STEEPEST_RAMP}

    checks: list[Check] = []
    blocked_by_level, blocked_no_wading, feasible_by_level = [], [], []
    for scenario in list_scenarios():
        snap = load_hazard(scenario).snapshot(g)
        level = f"{scenario.order} {scenario.title}"
        same, over, cost_bad, monotone_bad, no_way_forward, on_steps, steps_avoided = 0, 0, 0, 0, 0, 0, 0
        on_steep, steep_avoided = 0, 0
        aid_monotone_bad = 0
        feasible_ankle = 0
        for o, d in pairs:
            feasible, feasible_manual = [], []
            for name, prof in travellers.items():
                plan = plan_routes(router, o.access_points, d.access_points, snap, prof)
                if (
                    scenario.order == 0
                    and plan.recommended.found
                    and plan.recommended.route.geometry.equals(plan.shortest.route.geometry)
                ):
                    same += 1
                for opt in (plan.recommended, plan.safe_shortest):
                    if opt.found and opt.metrics.segments_over_limit:
                        over += 1
                if plan.recommended.found:
                    cost = risk_cost(snap, prof)
                    rec = route_cost(plan.recommended.route, g, cost)
                    safe = route_cost(plan.safe_shortest.route, g, cost)
                    short = route_cost(plan.shortest.route, g, cost)
                    if rec is None or rec > safe + 1e-6 or (short is not None and rec > short + 1e-6):
                        cost_bad += 1
                if name in {p.label for p in parts}:
                    feasible.append(plan.recommended.found)
                if name in manual_levels:
                    feasible_manual.append(plan.recommended.found)
                if name == BodyPart.ANKLE.label:
                    feasible_ankle += plan.recommended.found
                trip = None
                if prof.uses_wheelchair or (not plan.recommended.found and name == BodyPart.ANKLE.label):
                    trip = plan_trip(router, refuges, o, d, snap, prof)
                if prof.uses_wheelchair:
                    planned = [opt.route for opt in plan.options]
                    planned += [
                        x.route for x in (trip.least_water, trip.refuge, trip.downgrade and trip.downgrade.option) if x
                    ]
                    on_steps += sum(1 for route in planned if route is not None and route.uses_steps)
                    steps_avoided += plan.steps_avoided
                    on_steep += sum(
                        1
                        for route in planned
                        if route is not None and any(seg.source_edge_id in steep for seg in route.segments)
                    )
                    steep_avoided += bool(_steep_avoided(plan))
                way_forward = trip is not None and (
                    trip.downgrade or trip.refuge or trip.origin.sheltered or trip.emergency
                )
                if trip is not None and not plan.recommended.found and not way_forward:
                    no_way_forward += 1
            monotone_bad += any(feasible[i] and not feasible[i + 1] for i in range(len(feasible) - 1))
            aid_monotone_bad += any(
                feasible_manual[i] and not feasible_manual[i + 1] for i in range(len(feasible_manual) - 1)
            )
        if scenario.order == 0:
            checks.append(
                Check("R-A", f"{level}: recommended = shortest (trip × traveller)", len(pairs) * len(travellers), same)
            )
        checks.append(Check("R-B", f"{level}: routes using water over the limit", 0, over))
        checks.append(Check("R-C", f"{level}: recommended costlier than an alternative", 0, cost_bad))
        checks.append(Check("R-D", f"{level}: trips possible with a stricter limit only", 0, monotone_bad))
        checks.append(Check("R-E", f"{level}: no-route trips with no way forward", 0, no_way_forward))
        checks.append(Check("R-G", f"{level}: mobility aid routes using steps", 0, on_steps))
        checks.append(
            Check("R-H", f"{level}: manual wheelchair trips possible at a lower level only", 0, aid_monotone_bad)
        )
        checks.append(
            Check("R-G", f"{level}: wheelchair trips whose plain shortest way has steps", "—", steps_avoided, True)
        )
        checks.append(Check("R-I", f"{level}: mobility aid routes using a path steeper than 1:14", 0, on_steep))
        checks.append(
            Check(
                "R-I", f"{level}: wheelchair trips whose plain shortest way has a steep path", "—", steep_avoided, True
            )
        )

        def over_limit(profile: TravellerProfile, snap=snap) -> int:
            return sum(
                1 for *_, e in g.edges(data=True) if model.edge_risk(snap.condition(source_edge_id(e)), profile) is None
            )

        blocked_by_level.append(over_limit(adult()))
        blocked_no_wading.append(over_limit(adult(BodyPart.NO_WADING)))
        feasible_by_level.append(feasible_ankle)
    # The original R-F prediction ("edges over the ankle limit rise strictly by level") failed on the
    # first run: light ponding is 3-5 cm by design, under the 6.6 cm ankle limit, so levels 0 and 1
    # both have none. It is replaced by the two revised predictions below (see docs/verification.md).
    checks.append(
        Check(
            "R-F",
            "(revised) edges over the ankle limit never fall by level",
            True,
            all(a <= b for a, b in itertools.pairwise(blocked_by_level)),
        )
    )
    checks.append(
        Check(
            "R-F",
            "(revised) edges over the no-wading limit rise strictly by level",
            True,
            all(a < b for a, b in itertools.pairwise(blocked_no_wading)),
        )
    )
    checks.append(
        Check(
            "R-F",
            "trips possible at the ankle limit never rise by level",
            True,
            all(a >= b for a, b in itertools.pairwise(feasible_by_level)),
        )
    )
    checks.append(Check("R-F", "edges over the ankle limit, by level", "—", tuple(blocked_by_level), True))
    checks.append(Check("R-F", "edges over the no-wading limit, by level", "—", tuple(blocked_no_wading), True))
    checks.append(Check("R-F", "trips possible at the ankle limit, by level", "—", tuple(feasible_by_level), True))
    return checks
