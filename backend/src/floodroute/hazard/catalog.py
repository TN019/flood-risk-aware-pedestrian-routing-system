"""The bundled flood scenarios.

Each scenario is defined by a small JSON file in ``data/scenarios/`` (committed) and, unless it is
dry, a depth grid built from it by ``scripts/make_scenarios.py`` into ``data/processed/scenarios/``.

Definition fields: ``id``, ``order`` (0 = normal, rising with severity), ``title``,
``description``, ``method`` and the method's parameters. Methods:

- ``none``: no water anywhere.
- ``terrain-fill``: depths from ``hazard.terrain.scenario_depths`` with parameters
  ``tide_level_m_ahd`` (null for no tide flooding), ``drain_backflow`` (the tide also enters
  through drain inlets) and ``ponding_fill_fraction``.

``level`` names the flood level (``risk.levels.FloodLevel``) the scenario stands for; its typical
depth must fall in that level's band (checked by the tests and by ``scripts/make_scenarios.py``).

``sources`` lists where each parameter comes from.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from floodroute import config
from floodroute.hazard.base import HazardProvider, NoHazard
from floodroute.hazard.grid import DepthGrid, GridHazard

NONE = "none"
TERRAIN_FILL = "terrain-fill"


@dataclass(frozen=True)
class ScenarioInfo:
    id: str
    order: int
    title: str
    description: str
    method: str
    params: dict = field(default_factory=dict)

    @property
    def grid_path(self) -> Path:
        return config.PROCESSED_DIR / "scenarios" / f"{self.id}.tif"


def read_definition(path: Path) -> ScenarioInfo:
    doc = json.loads(Path(path).read_text())
    known = {"id", "order", "title", "description", "method"}
    return ScenarioInfo(
        id=doc["id"],
        order=int(doc["order"]),
        title=doc["title"],
        description=doc.get("description", ""),
        method=doc["method"],
        params={k: v for k, v in doc.items() if k not in known},
    )


def list_scenarios(directory: Path = config.SCENARIO_DIR) -> list[ScenarioInfo]:
    """Bundled scenarios, from normal conditions to the most severe."""
    return sorted((read_definition(p) for p in Path(directory).glob("*.json")), key=lambda s: s.order)


def load_hazard(info: ScenarioInfo) -> HazardProvider:
    if info.method == NONE:
        return NoHazard()
    if info.method == TERRAIN_FILL:
        if not info.grid_path.exists():
            raise FileNotFoundError(f"{info.grid_path} is missing; run scripts/make_scenarios.py")
        return GridHazard(DepthGrid.read(info.grid_path), source=f"scenario:{info.id}")
    raise ValueError(f"unknown scenario method {info.method!r}")
