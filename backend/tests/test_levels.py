import networkx as nx
import pytest
from shapely.geometry import LineString

from floodroute import config
from floodroute.hazard import DRY, EdgeCondition, HazardSnapshot
from floodroute.risk.levels import REFERENCE_HEIGHT_M, FloodLevel, level_of, typical_depth_m


def test_bands_follow_ankle_knee_and_hip_of_the_reference_adult():
    assert REFERENCE_HEIGHT_M == 1.70
    assert FloodLevel.LIGHT.upper_m == pytest.approx(0.0663)
    assert FloodLevel.MODERATE.upper_m == pytest.approx(0.4845)
    assert FloodLevel.HEAVY.upper_m == pytest.approx(0.901)
    assert FloodLevel.EXTREME.upper_m is None
    assert FloodLevel.MODERATE.lower_m == FloodLevel.LIGHT.upper_m


@pytest.mark.parametrize(
    "depth, level",
    [
        (0.05, FloodLevel.LIGHT),
        (0.0663, FloodLevel.LIGHT),
        (0.07, FloodLevel.MODERATE),
        (0.48, FloodLevel.MODERATE),
        (0.49, FloodLevel.HEAVY),
        (0.90, FloodLevel.HEAVY),
        (0.95, FloodLevel.EXTREME),
        (3.0, FloodLevel.EXTREME),
    ],
)
def test_level_of_a_depth(depth, level):
    assert level_of(depth) is level


def street(*lengths, inside=True):
    g = nx.Graph(crs=config.METRIC_CRS)
    x = 0.0
    for i, length in enumerate(lengths):
        geom = LineString([(x, 0), (x + length, 0)])
        g.add_edge(i, i + 1, geometry=geom, length_m=length, edge_id=f"e{i}", in_study_area=inside)
        x += length
    return g


def test_typical_depth_is_the_length_weighted_median_of_wet_edges():
    g = street(100, 10, 10, 50)
    conditions = {
        "e0": EdgeCondition(0.10),  # 100 of the 120 known wet metres
        "e1": EdgeCondition(0.40),
        "e2": EdgeCondition(0.60),
        "e3": EdgeCondition(None),  # unknown depth: left out
    }
    assert typical_depth_m(HazardSnapshot("t", conditions=conditions, default=DRY), g) == pytest.approx(0.10)


def test_typical_depth_uses_wet_length_and_ignores_edges_outside_the_area():
    conditions = {
        "e0": EdgeCondition(0.10, flooded_length_m=10),
        "e1": EdgeCondition(0.40, flooded_length_m=60),
    }
    snap = HazardSnapshot("t", conditions=conditions, default=DRY)
    assert typical_depth_m(snap, street(100, 100)) == pytest.approx(0.40)
    assert typical_depth_m(snap, street(100, 100, inside=False)) is None
    assert typical_depth_m(HazardSnapshot("t", conditions={}, default=DRY), street(100, 100)) is None
