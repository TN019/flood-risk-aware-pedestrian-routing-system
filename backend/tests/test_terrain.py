import networkx as nx
import numpy as np
import pytest
from affine import Affine
from shapely.geometry import LineString

from floodroute import config
from floodroute.hazard.grid import DepthGrid, GridHazard, edge_conditions
from floodroute.hazard.terrain import (
    PIT_TOLERANCE_M,
    WATER_SURFACE_M,
    Terrain,
    depression_ponding,
    inlet_cells,
    river_inundation,
    scenario_depths,
    walking_surface,
)

CELL = 5.0
TRANSFORM = Affine.translation(0, 100) @ Affine.scale(CELL, -CELL)  # 20 x 20 cells over (0,0)-(100,100)


def terrain(ground):
    ground = np.asarray(ground, dtype="float32")
    return Terrain(ground, ground <= WATER_SURFACE_M, TRANSFORM, config.METRIC_CRS)


def river_valley():
    """A river in the first two columns, low ground beside it rising to a ridge at column 10, and
    an equally low basin behind the ridge."""
    ground = np.full((20, 20), 3.0, dtype="float32")
    ground[:, :2] = 0.0  # river surface
    ground[:, 2:10] = np.linspace(1.0, 2.6, 8)  # bank rising away from the river
    ground[:, 10] = 4.0  # ridge
    ground[:, 12:16] = 1.2  # basin, lower than the bank but cut off from the river
    return ground


# ------------------------------------------------------------------ walking surface


def test_river_cells_take_the_bank_elevation():
    z = np.full((9, 9), 2.0, dtype="float32")
    z[:, :3] = 0.0
    out = walking_surface(z)
    assert np.allclose(out[:, :3], 2.0)


def test_narrow_pit_is_lifted_close_to_its_surroundings():
    z = np.full((9, 9), 2.0, dtype="float32")
    z[4, 4] = -4.0  # a 5 m wide pit, e.g. a basement ramp
    out = walking_surface(z)
    assert out[4, 4] >= 2.0 - PIT_TOLERANCE_M - 1e-6


# ------------------------------------------------------------------ river inundation


def test_river_floods_connected_low_ground_only():
    t = terrain(river_valley())
    depth = river_inundation(t, 1.8)
    assert depth[5, 2] == pytest.approx(0.8)  # bank at 1.0 m under 1.8 m of water
    assert depth[5, 9] == 0  # bank at 2.6 m is above the water
    assert (depth[:, 12:16] == 0).all()  # low basin behind the ridge stays dry
    assert (depth[:, :2] == 0).all()  # the river itself is not walking ground


def test_drain_inlet_lets_the_tide_into_ground_cut_off_from_the_river():
    t = terrain(river_valley())
    inlets = np.zeros((20, 20), dtype=bool)
    inlets[5, 13] = True  # a pit in the basin behind the ridge
    depth = river_inundation(t, 1.8, inlets)
    assert depth[5, 13] == pytest.approx(0.6)  # basin ground 1.2 m
    assert (depth[:, 12:16] > 0).all()  # water spreads across the connected basin
    assert depth[5, 2] == pytest.approx(0.8)  # river side unchanged


def test_drain_inlet_above_the_tide_lets_nothing_in():
    t = terrain(river_valley())
    inlets = np.zeros((20, 20), dtype=bool)
    inlets[5, 17] = True  # on 3.0 m ground
    assert (river_inundation(t, 1.8, inlets)[:, 11:] == 0).all()


def test_inlet_points_map_to_their_cells():
    import geopandas as gpd
    from shapely.geometry import Point

    t = terrain(river_valley())
    points = gpd.GeoDataFrame(geometry=[Point(67.5, 72.5), Point(500, 500)], crs=config.METRIC_CRS)
    cells = inlet_cells(t, points)
    assert cells.sum() == 1 and cells[5, 13]  # the point off the grid is ignored


def test_river_flood_grows_with_the_level():
    t = terrain(river_valley())
    low, high = river_inundation(t, 1.6), river_inundation(t, 2.4)
    assert (high >= low).all() and (high > 0).sum() > (low > 0).sum()


# ------------------------------------------------------------------ stormwater ponding


def bowl():
    ground = np.full((20, 20), 3.0, dtype="float32")
    ground[8:12, 8:12] = 2.0  # a 20 m depression, 1 m deep, that spills at 3.0 m
    ground[9:11, 9:11] = 1.8
    return ground


def test_depression_fills_to_its_spill_point():
    t = terrain(bowl())
    everywhere = np.ones((20, 20), dtype=bool)
    full = depression_ponding(t, everywhere, 1.0)
    assert full[10, 10] == pytest.approx(1.2)  # spill 3.0 - bottom 1.8
    assert full[8, 8] == pytest.approx(1.0)
    assert full[0, 0] == 0


def test_partly_filled_depression_rises_from_its_lowest_point():
    t = terrain(bowl())
    half = depression_ponding(t, np.ones((20, 20), dtype=bool), 0.5)
    assert half[10, 10] == pytest.approx(0.6)  # level 1.8 + 0.5 x 1.2 = 2.4
    assert half[8, 8] == pytest.approx(0.4)


def test_ponding_only_inside_the_given_areas():
    t = terrain(bowl())
    assert (depression_ponding(t, np.zeros((20, 20), dtype=bool), 1.0) == 0).all()


def test_ground_every_high_tide_would_reach_has_unknown_depth():
    ground = river_valley()
    ground[:, 2] = 0.3  # a strip beside the river below the highest tide: not a real walking surface
    grid = scenario_depths(terrain(ground), 1.8, 0.0)
    assert np.isnan(grid.depth_m[:, 2]).all()
    assert grid.depth_m[5, 3] > 0 and not np.isnan(grid.depth_m[5, 3])


# ------------------------------------------------------------------ depth grid on a network


def network(*lines, bridge=None):
    g = nx.Graph(crs=config.METRIC_CRS)
    for i, coords in enumerate(lines):
        g.add_edge(2 * i, 2 * i + 1, geometry=LineString(coords), edge_id=f"e{i}", is_bridge=(i == bridge))
    return g


def test_edge_takes_its_deepest_depth_and_wet_length():
    depth = np.zeros((20, 20), dtype="float32")
    depth[:, 10:] = 0.3  # x >= 50 m
    g = network([(10, 50), (90, 50)])
    c = edge_conditions(DepthGrid(depth, TRANSFORM, config.METRIC_CRS), g)["e0"]
    assert c.depth_m == pytest.approx(0.3)
    assert c.flooded_length_m == pytest.approx(40, abs=3)


def test_bridges_are_dry_and_missing_data_is_unknown():
    depth = np.full((20, 20), 1.0, dtype="float32")
    depth[0, 0] = np.nan
    g = network([(10, 50), (90, 50)], [(0, 99), (30, 99)], [(50, 50), (150, 50)], bridge=0)
    conditions = GridHazard(DepthGrid(depth, TRANSFORM, config.METRIC_CRS), "test").snapshot(g).conditions
    assert "e0" not in conditions  # bridge deck above the water
    assert conditions["e1"].depth_m is None  # crosses a no-data cell
    assert conditions["e2"].depth_m is None  # runs off the grid
