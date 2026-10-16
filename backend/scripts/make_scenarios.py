"""Build the depth grid of every bundled flood scenario and check its level.

Reads the definitions in data/scenarios/*.json and writes data/processed/scenarios/<id>.tif. When
the processed network exists, each scenario's typical depth on flooded footpaths is compared with
the band of the level it stands for.

Inputs (scripts/download_data.py --only dem pits):
- Geoscience Australia 5 m LiDAR DEM (data/raw/dem_5m_southbank.tif)
- City of Melbourne stormwater pits (data/raw/stormwater_pits_southbank.geojson)

Run:  uv run python scripts/make_scenarios.py
"""

from __future__ import annotations

import numpy as np

from floodroute import config
from floodroute.hazard.base import DRY_DEPTH_M
from floodroute.hazard.catalog import TERRAIN_FILL, list_scenarios, load_hazard
from floodroute.hazard.terrain import Terrain, inlet_cells, scenario_depths
from floodroute.risk.levels import FloodLevel, level_of, typical_depth_m
from floodroute.sources.drainage import surface_inlets


def main() -> None:
    terrain = Terrain.read(config.DEM_PATH)
    inlets = inlet_cells(terrain, surface_inlets())
    land = ~terrain.water & ~np.isnan(terrain.ground_m)
    graph = None
    if config.PROCESSED_NETWORK_PATH.exists():
        from floodroute.network import load_graph

        graph = load_graph(config.PROCESSED_NETWORK_PATH)
    mismatched = []
    for info in list_scenarios():
        if info.method != TERRAIN_FILL:
            print(f"{info.order} {info.title}: no water")
            continue
        p = info.params
        grid = scenario_depths(
            terrain, p["tide_level_m_ahd"], p["ponding_fill_fraction"], inlets if p.get("drain_backflow") else None
        )
        grid.write(info.grid_path)
        wet = (np.nan_to_num(grid.depth_m) > DRY_DEPTH_M) & land
        line = f"{info.order} {info.title}: {wet.sum() / land.sum():.1%} of the ground wet"
        if graph is not None:
            depth = typical_depth_m(load_hazard(info).snapshot(graph), graph)
            actual = level_of(depth)
            line += f"; typical depth {depth * 100:.0f} cm ({actual.label})"
            if actual is not FloodLevel[p["level"].upper()]:
                mismatched.append(info.id)
                line += f" -- expected {p['level']}"
        print(line + f" -> {info.grid_path.relative_to(config.REPO_ROOT)}")
    if mismatched:
        raise SystemExit(f"typical depth outside the stated level: {', '.join(mismatched)}")


if __name__ == "__main__":
    main()
