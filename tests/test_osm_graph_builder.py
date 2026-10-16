import itertools

import networkx as nx
import pytest
from shapely.geometry import Point, box

import osm_graph_builder as ob
from routing import Router

CRS = "EPSG:7855"
_way_ids = itertools.count(1)


def osm_graph(nodes: dict, ways: list) -> nx.MultiDiGraph:
    """An unsimplified osmnx-style walk graph: every way is added in both directions."""
    g = nx.MultiDiGraph(crs=CRS)
    for n, (x, y) in nodes.items():
        g.add_node(n, x=x, y=y)
    for path, tags in ways:
        osmid = next(_way_ids)
        for u, v in zip(path, path[1:]):
            length = Point(nodes[u]).distance(Point(nodes[v]))
            g.add_edge(u, v, osmid=osmid, length=length, reversed=False, **tags)
            g.add_edge(v, u, osmid=osmid, length=length, reversed=True, **tags)
    return g


def build(nodes, ways, **kw):
    graph, report = ob.build_graph_from_osm(osm_graph(nodes, ways), CRS, **kw)
    return graph, report


def test_indoor_private_and_sidepath_ways_are_excluded():
    nodes = {1: (0, 0), 2: (100, 0), 3: (200, 0), 4: (300, 0), 5: (400, 0), 6: (500, 0)}
    ways = [([1, 2], {"highway": "footway"}),
            ([2, 3], {"highway": "corridor"}),
            ([3, 4], {"highway": "footway", "indoor": "yes"}),
            ([4, 5], {"highway": "service", "foot": "private"}),
            ([5, 6], {"highway": "primary", "foot": "use_sidepath"})]
    graph, report = build(nodes, ways, keep_all_components=True)
    assert (report.indoor_removed, report.private_removed, report.use_sidepath_removed) == (4, 2, 2)  # directed
    assert {frozenset((u, v)) for u, v in graph.edges()} == {frozenset((1, 2))}


def test_ways_crossing_without_a_shared_node_stay_unconnected():
    nodes = {1: (0, 0), 2: (100, 0), 3: (50, -50), 4: (50, 50)}
    ways = [([1, 2], {"highway": "footway", "bridge": "yes"}), ([3, 4], {"highway": "footway"})]
    graph, _ = build(nodes, ways, keep_all_components=True)
    assert nx.number_connected_components(graph) == 2


def test_degree_two_chains_are_simplified_but_tag_changes_are_kept():
    nodes = {1: (0, 0), 2: (50, 0), 3: (100, 0), 4: (150, 0)}
    ways = [([1, 2, 3], {"highway": "footway", "name": "A"}), ([3, 4], {"highway": "steps", "name": "A"})]
    graph, report = build(nodes, ways)
    assert graph.number_of_edges() == 2  # 1-3 merged; 3 kept because highway changes
    lengths = sorted(round(d["length_m"]) for *_, d in graph.edges(data=True))
    assert lengths == [50, 100]
    assert report.steps == 1


def test_carriageway_with_sidewalks_is_kept_but_penalised():
    # A road 1-2-3 with sidewalks on both sides that only touch the road at the corner nodes 1 and 3,
    # like many OSM sidewalks. Removing the road would disconnect the two sidewalks.
    nodes = {1: (0, 0), 2: (100, 0), 3: (200, 0), 11: (0, 8), 12: (200, 8), 21: (0, -8), 22: (200, -8),
             30: (200, 100)}
    ways = [([1, 2, 3], {"highway": "primary"}),
            ([1, 11, 12, 3], {"highway": "footway", "footway": "sidewalk"}),
            ([1, 21, 22, 3], {"highway": "footway", "footway": "sidewalk"}),
            ([3, 30], {"highway": "footway"})]
    graph, report = build(nodes, ways)
    assert nx.is_connected(graph)
    road = [d for *_, d in graph.edges(data=True) if d["highway"] == "primary"]
    assert len(road) == 1 and road[0]["cost_factor"] == ob.CARRIAGEWAY_PENALTY and road[0]["is_carriageway"]
    assert report.carriageway_with_sidewalk_penalised == 1
    # Routing along the block uses a sidewalk (216 m), not the 200 m carriageway.
    route = Router(graph).route(Point(0, 8), Point(200, 8))
    assert route.length_m == pytest.approx(200)
    route = Router(graph).route(Point(0, 0), Point(200, 0))
    assert route.length_m == pytest.approx(216)


def test_carriageway_without_sidewalk_is_not_penalised():
    nodes = {1: (0, 0), 2: (200, 0), 3: (200, 100)}
    ways = [([1, 2], {"highway": "residential"}), ([2, 3], {"highway": "footway"})]
    graph, _ = build(nodes, ways)
    road = next(d for *_, d in graph.edges(data=True) if d["highway"] == "residential")
    assert road["cost_factor"] == 1.0


def test_study_area_clip_and_flags():
    # Study area x <= 150, buffer reaches x <= 350. Names differ so simplification keeps the ways apart.
    nodes = {1: (0, 0), 2: (100, 0), 3: (300, 0), 4: (1000, 0), 5: (2000, 0), 6: (2100, 0)}
    ways = [([1, 2], {"highway": "footway", "name": "A"}), ([2, 3], {"highway": "footway", "name": "B"}),
            ([3, 4], {"highway": "footway", "name": "C"}),  # starts inside the buffer: kept whole
            ([5, 6], {"highway": "footway", "name": "D"})]  # entirely outside: removed (both directions)
    graph, report = build(nodes, ways, study_area=box(-10, -10, 150, 10), buffer_m=200)
    assert report.outside_area_removed == 2
    flags = sorted((round(d["length_m"]), d["in_study_area"]) for *_, d in graph.edges(data=True))
    assert flags == [(100, True), (200, True), (700, False)]
