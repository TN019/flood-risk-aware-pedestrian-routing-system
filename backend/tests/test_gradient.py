"""Footpath gradients: which surveyed sections are trusted, and how an edge takes its gradient from
them. That mobility aid users never use a steep path is tested in test_access.py."""

import json

import geopandas as gpd
import networkx as nx
import pytest
from shapely.geometry import LineString, box, mapping

from floodroute import config
from floodroute.network.gradient import (
    NEAR_BRIDGE,
    SHORT,
    TRUSTED,
    TWO_LEVELS,
    add_gradients,
    classify_sections,
)
from floodroute.sources.steepness import load_footpath_sections


def sections(*rows) -> gpd.GeoDataFrame:
    """Sections from (polygon, gradient, run, rise)."""
    return gpd.GeoDataFrame(
        {
            "section_id": range(len(rows)),
            "gradient": [r[1] for r in rows],
            "run_m": [r[2] for r in rows],
            "rise_m": [r[3] for r in rows],
        },
        geometry=gpd.GeoSeries([r[0] for r in rows], crs=config.METRIC_CRS),
    )


def graph(*lines, **flags) -> nx.Graph:
    """One edge per line (e0, e1, …); ``flags`` maps an edge id to its extra attributes."""
    g = nx.Graph(crs=config.METRIC_CRS)
    for i, line in enumerate(lines):
        u, v = line.coords[0], line.coords[-1]
        for n in (u, v):
            g.add_node(n, x=n[0], y=n[1], kind="junction", in_study_area=True)
        g.add_edge(
            u, v, geometry=line, length_m=line.length, edge_id=f"e{i}", cost_factor=1.0, **flags.get(f"e{i}", {})
        )
    return g


def gradient_of(line, *rows, **flags) -> float | None:
    g = graph(line, **flags)
    add_gradients(g, sections(*rows))
    return next(iter(g.edges(data=True)))[2]["gradient"]


STREET = LineString([(0, 0), (100, 0)])


def strip(x0, x1, y0=-1.5, y1=1.5):
    return box(x0, y0, x1, y1)


def test_short_sections_sections_near_bridges_and_two_level_sections_are_not_trusted():
    g = graph(STREET, LineString([(0, 50), (100, 50)]), e1={"is_bridge": True})
    s = sections(
        (strip(0, 4), 0.20, 4.0, 0.8),  # a kerb ramp
        (strip(0, 30, 47, 49), 0.03, 30.0, 0.9),  # 1 m from the bridge
        (strip(0, 10), 0.30, 10.0, 3.0),  # 3 m up in 10 m: two levels
        (strip(0, 100), 0.03, 100.0, 3.0),  # 3 m up in 100 m: a long gentle slope
        (strip(0, 15), 0.10, 15.0, 1.5),  # a steep ramp
    )
    assert classify_sections(s, g) == [SHORT, NEAR_BRIDGE, TWO_LEVELS, TRUSTED, TRUSTED]


def test_an_edge_takes_the_gradient_of_the_section_it_runs_along():
    assert gradient_of(STREET, (strip(0, 100), 0.10, 100.0, 1.0)) == pytest.approx(0.10)
    assert gradient_of(STREET, (strip(40, 60), 0.10, 20.0, 2.0)) == pytest.approx(0.10)  # 20 m of it
    assert gradient_of(STREET, (strip(0, 100, 1.5, 5), 0.10, 100.0, 1.0)) == pytest.approx(0.10)  # 1.5 m away
    assert gradient_of(STREET, (strip(0, 100, 2.5, 5), 0.10, 100.0, 1.0)) is None  # 2.5 m away
    assert gradient_of(STREET) is None


def test_overlapping_sections_must_agree_before_a_stretch_counts_as_steep():
    flat_all_along = (strip(0, 100), 0.02, 100.0, 2.0)
    steep_middle = (strip(40, 60), 0.10, 20.0, 2.0)
    assert gradient_of(STREET, flat_all_along, steep_middle) == pytest.approx(0.02)
    flat_east = (strip(60, 100), 0.02, 40.0, 0.8)
    assert gradient_of(STREET, flat_east, steep_middle) == pytest.approx(0.10)  # they meet, not overlap


def test_a_steep_stretch_must_be_at_least_5_m_long():
    # A section reaches 2 m beyond its ends: 0.5 m of section covers 4.5 m of the edge, 1 m covers 5 m.
    assert gradient_of(STREET, (strip(40, 40.5), 0.10, 6.0, 0.6)) is None
    assert gradient_of(STREET, (strip(40, 41), 0.10, 6.0, 0.6)) == pytest.approx(0.10)
    flat = (strip(0, 100), 0.02, 100.0, 2.0)
    assert gradient_of(STREET, flat, (strip(40, 43), 0.10, 6.0, 0.6)) == pytest.approx(0.02)
    short = LineString([(0, 0), (3, 0)])
    assert gradient_of(short, (strip(-5, 5), 0.10, 10.0, 1.0)) == pytest.approx(0.10)  # the whole edge
    assert gradient_of(short, (strip(3.5, 8), 0.10, 10.0, 1.0)) is None  # reaches only its east end


def test_bridges_and_tunnels_take_no_gradient():
    ramp = (strip(0, 100), 0.10, 100.0, 1.0)
    assert gradient_of(STREET, ramp, e0={"is_tunnel": True}) is None
    assert gradient_of(STREET, ramp, e0={"is_bridge": True}) is None


def test_the_report_counts_sections_and_edges():
    g = graph(STREET, LineString([(0, 30), (100, 30)]))
    report = add_gradients(g, sections((strip(0, 100), 0.10, 100.0, 1.0), (strip(0, 3, 28, 32), 0.2, 3.0, 0.6)))
    assert (report.sections, report.short, report.trusted, report.trusted_steeper_than_ramp) == (2, 1, 1, 1)
    assert (report.edges_with_gradient, report.edges_steeper_than_ramp) == (1, 1)


def test_the_export_is_merged_into_one_section_per_footpath(tmp_path):
    def feature(poly, mcc_id, gradepc, distance=10.82, deltaz=0.96):
        props = {"mcc_id": mcc_id, "gradepc": gradepc, "distance": distance, "deltaz": deltaz}
        props |= {"rlmin": 2.22, "rlmax": 3.18, "address": "Southbank Promenade"}
        return {"type": "Feature", "geometry": mapping(poly), "properties": props}

    w, h = 1e-4, 2e-5  # degrees, near Southbank
    x, y = 144.964, -37.820
    features = [
        feature(box(x, y, x + w, y + h), 1, 8.87),
        feature(box(x + w, y, x + 2 * w, y + h), 1, 8.87),  # a second piece of the same section
        feature(box(x, y + h, x + w, y + 2 * h), 1, None, None, None),  # a piece without values
        feature(box(x, y + 3 * h, x + w, y + 4 * h), 2, 1.5, 40.0, 0.6),
    ]
    path = tmp_path / "steepness.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    s = load_footpath_sections(path).sort_values("section_id")
    assert list(s.section_id) == [1, 2] and list(s.gradient) == pytest.approx([0.0887, 0.015])
    assert s.crs == config.METRIC_CRS
    assert s.geometry.iloc[0].area == pytest.approx(2 * s.geometry.iloc[1].area, rel=0.01)
    assert (s.run_m.iloc[0], s.rise_m.iloc[0], s.level_max_m.iloc[0]) == (10.82, 0.96, 3.18)
