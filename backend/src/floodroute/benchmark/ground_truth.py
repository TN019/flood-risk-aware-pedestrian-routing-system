"""Inspecting the data on site (ground truthing): a stratified sample, and the comparison.

The program can check that routes follow its rules on the data it has; only an inspection can tell
whether that data matches the street. ``sample`` draws footpath sections (by kind) and building
entrances, and records what the model says about each; an inspector fills the ``field_`` columns on
site; ``compare`` measures the agreement, and above all the share of items the model treats as
usable or step-free that are not (the false accessible rate).

Field answers are ``yes``, ``no`` or ``unknown`` unless stated; ``field_gradient`` is ``flat``,
``gentle`` or ``steep``.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

from pyproj import Transformer

from floodroute import config
from floodroute.benchmark.world import World

MODEL_COLUMNS = [
    "id",
    "kind",  # "path" or "entrance"
    "category",
    "lat",
    "lon",
    "name",
    "osm_ref",
    "model_steps",  # paths: the section is a flight of steps
    "model_step_free",  # paths: usable by wheelchair users; entrances: n/a
    "model_entrance",  # entrances: "mapped door" or "outline point" (no door mapped)
]
FIELD_COLUMNS = [
    "field_date",
    "inspector",
    "field_found",  # the section or entrance exists where shown
    "field_passable",  # on foot
    "field_steps",
    "field_kerb_ramp",  # crossings and kerbs: yes / no / n/a
    "field_gradient",
    "field_width_m",
    "field_surface",
    "field_barrier_or_closed",
    "field_entrance_step_free",
    "field_open_to_public",
    "field_photo",
    "field_notes",
]
PATH_KINDS = ("steps", "crossing", "beside carriageway", "footpath", "street")


def path_category(data: dict) -> str:
    if data.get("is_steps"):
        return "steps"
    if data.get("is_crossing"):
        return "crossing"
    if data.get("is_carriageway"):
        return "beside carriageway"
    if data.get("highway") in ("footway", "pedestrian", "path"):
        return "footpath"
    return "street"


def sample(world: World, per_kind: int = 15, seed: int = 2026) -> list[dict]:
    """``per_kind`` footpath sections of each kind and ``per_kind`` building entrances, inside
    Southbank."""
    rng = random.Random(seed)
    to_wgs = Transformer.from_crs(config.METRIC_CRS, "EPSG:4326", always_xy=True)
    area = world.graph.graph["study_area"]

    def latlon(p) -> tuple[float, float]:
        lon, lat = to_wgs.transform(p.x, p.y)
        return round(lat, 6), round(lon, 6)

    by_kind: dict[str, list] = {k: [] for k in PATH_KINDS}
    for _, _, d in world.graph.edges(data=True):
        if d.get("in_study_area"):
            by_kind[path_category(d)].append(d)
    rows = []
    for kind in PATH_KINDS:
        for d in rng.sample(by_kind[kind], min(per_kind, len(by_kind[kind]))):
            lat, lon = latlon(d["geometry"].interpolate(0.5, normalized=True))
            rows.append(
                {
                    "id": f"path-{d['edge_id']}",
                    "kind": "path",
                    "category": kind,
                    "lat": lat,
                    "lon": lon,
                    "name": d.get("name") or "",
                    "osm_ref": d.get("osmid", ""),
                    "model_steps": "yes" if d.get("is_steps") else "no",
                    "model_step_free": "no" if d.get("is_steps") else "yes",
                    "model_entrance": "",
                }
            )
    buildings = world.resolver.buildings
    inside = [i for i, g in enumerate(buildings.geometry) if area.contains(g.representative_point())]
    for i in rng.sample(inside, min(per_kind, len(inside))):
        geom = buildings.geometry[i]
        place = world.resolver.resolve(geom.representative_point(), "building")
        if not place.access:
            continue
        point = place.access[0].point
        lat, lon = latlon(point)
        name = buildings.at[i, "name"] if "name" in buildings and isinstance(buildings.at[i, "name"], str) else ""
        rows.append(
            {
                "id": f"entrance-{i}",
                "kind": "entrance",
                "category": "building entrance",
                "lat": lat,
                "lon": lon,
                "name": name,
                "osm_ref": "",
                "model_steps": "",
                "model_step_free": "",
                "model_entrance": "mapped door" if place.method == "entrances" else "outline point",
            }
        )
    for row in rows:
        row.update(dict.fromkeys(FIELD_COLUMNS, ""))
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MODEL_COLUMNS + FIELD_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return [
            {k: (v or "").strip().lower() if k.startswith(("field_", "model_")) else v for k, v in r.items()}
            for r in csv.DictReader(f)
        ]


def _rate(n: int, of: int) -> dict:
    return {"count": n, "of": of, "rate": n / of if of else None}


def compare(rows: list[dict]) -> dict:
    """Agreement between the model and an inspection, for the rows inspected (``field_found``
    filled)."""
    inspected = [r for r in rows if r.get("field_found") in ("yes", "no")]
    paths = [r for r in inspected if r["kind"] == "path"]
    entrances = [r for r in inspected if r["kind"] == "entrance"]

    def not_passable(r: dict) -> bool:
        return r["field_found"] == "no" or r.get("field_passable") == "no" or r.get("field_barrier_or_closed") == "yes"

    def not_step_free(r: dict) -> bool:
        return not_passable(r) or r.get("field_steps") == "yes" or r.get("field_kerb_ramp") == "no"

    known_steps = [r for r in paths if r.get("field_steps") in ("yes", "no")]
    step_free_claims = [r for r in paths if r["model_step_free"] == "yes"]
    by_kind = {}
    for kind in PATH_KINDS:
        rs = [r for r in paths if r["category"] == kind]
        if rs:
            by_kind[kind] = {
                "inspected": len(rs),
                "not_passable": _rate(sum(map(not_passable, rs)), len(rs)),
                "step_free_but_not": _rate(
                    sum(1 for r in rs if r["model_step_free"] == "yes" and not_step_free(r)),
                    sum(1 for r in rs if r["model_step_free"] == "yes"),
                ),
            }
    return {
        "inspected": len(inspected),
        "paths": {
            "inspected": len(paths),
            # The model treats every section as walkable: any that is not is a false accessible.
            "false_accessible": _rate(sum(map(not_passable, paths)), len(paths)),
            "false_step_free": _rate(sum(map(not_step_free, step_free_claims)), len(step_free_claims)),
            "steps_agree": _rate(sum(1 for r in known_steps if r["model_steps"] == r["field_steps"]), len(known_steps)),
            "steps_missed": _rate(
                sum(1 for r in known_steps if r["model_steps"] == "no" and r["field_steps"] == "yes"),
                sum(1 for r in known_steps if r["model_steps"] == "no"),
            ),
            "by_kind": by_kind,
        },
        "entrances": {
            "inspected": len(entrances),
            "not_usable": _rate(
                sum(1 for r in entrances if r["field_found"] == "no" or r.get("field_open_to_public") == "no"),
                len(entrances),
            ),
            "not_step_free": _rate(
                sum(1 for r in entrances if r.get("field_entrance_step_free") == "no"),
                sum(1 for r in entrances if r.get("field_entrance_step_free") in ("yes", "no")),
            ),
        },
    }
