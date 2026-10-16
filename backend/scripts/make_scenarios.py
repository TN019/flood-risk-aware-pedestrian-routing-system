"""Build the depth grid of every bundled flood scenario.

Reads the definitions in data/scenarios/*.json and writes data/processed/scenarios/<id>.tif.

Input (scripts/download_data.py --only dem): Geoscience Australia 5 m LiDAR DEM
(data/raw/dem_5m_southbank.tif).

Run:  uv run python scripts/make_scenarios.py
"""

from __future__ import annotations

import numpy as np

from floodroute import config
from floodroute.hazard.base import DRY_DEPTH_M
from floodroute.hazard.catalog import TERRAIN_FILL, list_scenarios
from floodroute.hazard.terrain import Terrain, scenario_depths


def main() -> None:
    terrain = Terrain.read(config.DEM_PATH)
    land = ~terrain.water & ~np.isnan(terrain.ground_m)
    for info in list_scenarios():
        if info.method != TERRAIN_FILL:
            print(f"{info.order} {info.title}: no water")
            continue
        river = info.params["river_level_m_ahd"]
        grid = scenario_depths(terrain, river, info.params["ponding_fill_fraction"])
        grid.write(info.grid_path)
        wet = (np.nan_to_num(grid.depth_m) > DRY_DEPTH_M) & land
        print(
            f"{info.order} {info.title}: river {'-' if river is None else f'{river} m AHD'}, "
            f"ponding {info.params['ponding_fill_fraction']:.0%}; {wet.sum() / land.sum():.1%} of the ground wet "
            f"-> {info.grid_path.relative_to(config.REPO_ROOT)}"
        )


if __name__ == "__main__":
    main()
