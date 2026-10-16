import geopandas as gpd
import networkx as nx
import pytest
from shapely.geometry import LineString, Point, box

from floodroute.network import JUNCTION, com_builder, load_graph, parcel_access_nodes, save_graph

CRS = "EPSG:7855"


def raw(lines, points=()):
    rows = [{"objectid": str(i), "neworkid": None, "geometry": g} for i, g in enumerate(lines)]
    rows += [{"objectid": f"p{i}", "neworkid": pid, "geometry": Point(xy)} for i, (pid, xy) in enumerate(points)]
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=CRS)


def node_at(graph, xy):
    return next(n for n, d in graph.nodes(data=True)
                if d["kind"] == JUNCTION and abs(d["x"] - xy[0]) < 1e-6 and abs(d["y"] - xy[1]) < 1e-6)


def test_lines_connect_only_at_shared_endpoints():
    # Two lines crossing in an X (e.g. a bridge over a path) must not create a junction.
    graph, report = com_builder.build_graph(raw([LineString([(0, 0), (10, 0)]), LineString([(5, -5), (5, 5)]),
                                        LineString([(10, 0), (10, 10)])]))
    assert report.components_dropped == 1  # the crossing line is its own component
    assert graph.number_of_edges() == 2


def test_duplicates_and_self_loops_removed():
    a = LineString([(0, 0), (10, 0)])
    loop = LineString([(10, 0), (15, 5), (10, 5), (10, 0)])
    graph, report = com_builder.build_graph(raw([a, LineString([(10, 0), (0, 0)]), loop]))
    assert report.duplicates_removed == 1
    assert report.self_loops_removed == 1
    assert graph.number_of_edges() == 1


def test_tjunction_splits_line_and_connects():
    main = LineString([(0, 0), (20, 0)])
    branch = LineString([(10, 0.01), (10, 10)])  # endpoint 1 cm off main's interior
    graph, report = com_builder.build_graph(raw([main, branch]))
    assert report.tjunction_splits == 1
    assert graph.number_of_edges() == 3
    assert nx.is_connected(graph)
    total = sum(d["length_m"] for *_, d in graph.edges(data=True))
    assert total == pytest.approx(20 + 10, abs=0.05)


def test_parcel_hub_is_not_a_through_route():
    # Street A-B is long; a parcel at P links to both A and B and would be a shortcut.
    street = LineString([(0, 0), (0, 100), (100, 100), (100, 0)])
    links = [LineString([(0, 0), (50, 0)]), LineString([(50, 0), (100, 0)])]
    graph, report = com_builder.build_graph(raw([street, *links], points=[("P1", (50, 0))]))
    assert report.parcel_hubs_split == 1
    stubs = parcel_access_nodes(graph)["P1"]
    assert len(stubs) == 2
    assert all(graph.degree(s) == 1 for s in stubs)
    a, b = node_at(graph, (0, 0)), node_at(graph, (100, 0))
    assert nx.shortest_path_length(graph, a, b, weight="length_m") == pytest.approx(300)
    assert all(d["is_parcel_link"] for u, v, d in graph.edges(data=True) if u in stubs or v in stubs)


def test_parallel_lines_get_midpoint_node():
    straight = LineString([(0, 0), (10, 0)])
    curved = LineString([(0, 0), (5, 5), (10, 0)])
    graph, report = com_builder.build_graph(raw([straight, curved]))
    assert report.parallel_edges_split == 1
    assert graph.number_of_edges() == 3
    a, b = node_at(graph, (0, 0)), node_at(graph, (10, 0))
    assert nx.shortest_path_length(graph, a, b, weight="length_m") == pytest.approx(10)


def test_study_area_keeps_buffer_and_flags_membership():
    area = box(0, 0, 100, 100)
    inside = LineString([(10, 10), (90, 10)])
    to_buffer = LineString([(90, 10), (150, 10)])  # leaves the area, ends 50 m into the buffer
    in_buffer = LineString([(150, 10), (150, 200)])  # touches the 100 m buffer only near its start
    far = LineString([(500, 500), (600, 500)])  # nowhere near
    graph, report = com_builder.build_graph(raw([inside, to_buffer, in_buffer, far]), study_area=area, buffer_m=100)
    assert report.lines_outside_area == 1
    assert graph.number_of_edges() == 3  # lines crossing the buffer edge are kept whole
    flags = {round(d["length_m"]): d["in_study_area"] for *_, d in graph.edges(data=True)}
    assert flags == {80: True, 60: True, 190: False}
    assert node_at(graph, (10, 10)) is not None
    assert graph.nodes[node_at(graph, (10, 10))]["in_study_area"]
    assert not graph.nodes[node_at(graph, (150, 200))]["in_study_area"]


def test_save_and_load_roundtrip(tmp_path):
    street = LineString([(0, 0), (0, 100), (100, 100)])
    link = LineString([(100, 100), (120, 100)])
    area = box(-10, -10, 50, 50)
    graph, _ = com_builder.build_graph(raw([street, link], points=[("P1", (120, 100))]), study_area=area, buffer_m=200)
    path = tmp_path / "g.gpkg"
    save_graph(graph, path)
    loaded = load_graph(path)
    assert nx.utils.graphs_equal(nx.Graph(graph.edges()), nx.Graph(loaded.edges()))
    assert parcel_access_nodes(loaded) == parcel_access_nodes(graph)
    assert loaded.graph["study_area"].equals(area) and loaded.graph["buffer_m"] == 200
    for u, v, d in loaded.edges(data=True):
        assert d["length_m"] == pytest.approx(graph.edges[u, v]["length_m"])
        assert d["in_study_area"] == graph.edges[u, v]["in_study_area"]
    for n, d in loaded.nodes(data=True):
        assert d["in_study_area"] == graph.nodes[n]["in_study_area"]
