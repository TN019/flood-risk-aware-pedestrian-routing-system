import networkx as nx
import pytest
from shapely.geometry import LineString, Point

from floodroute.hazard import DRY, UNKNOWN, EdgeCondition, HazardSnapshot, NoHazard
from floodroute.risk import walking_cost
from floodroute.routing import NetworkXDijkstra, NoPathError, Router


def square():
    """Four 100 m sides; the a-b edge is discouraged with cost_factor 4."""
    g = nx.Graph(crs="EPSG:7855")
    xy = {"a": (0, 0), "b": (100, 0), "c": (100, 100), "d": (0, 100)}
    for n, (x, y) in xy.items():
        g.add_node(n, x=x, y=y, kind="junction", in_study_area=True)
    for i, (u, v) in enumerate((("a", "b"), ("b", "c"), ("c", "d"), ("d", "a"))):
        geom = LineString([xy[u], xy[v]])
        g.add_edge(u, v, geometry=geom, length_m=100.0, edge_id=f"e{i}", in_study_area=True,
                   cost_factor=4.0 if (u, v) == ("a", "b") else 1.0)
    return g


def test_walking_cost_scales_length_by_cost_factor():
    assert walking_cost("a", "b", {"length_m": 50.0, "cost_factor": 3.0}) == 150.0
    assert walking_cost("a", "b", {"length_m": 50.0}) == 50.0


def test_networkx_dijkstra_respects_cost_and_impassable_edges():
    g = square()
    finder = NetworkXDijkstra()
    assert finder.find_path(g, "a", "b", walking_cost) == ["a", "d", "c", "b"]  # 300 around beats 400 direct
    blocked = lambda u, v, d: None if {u, v} == {"a", "d"} else walking_cost(u, v, d)  # noqa: E731
    assert finder.find_path(g, "a", "c", blocked) == ["a", "b", "c"]
    all_blocked = lambda u, v, d: None  # noqa: E731
    with pytest.raises(NoPathError):
        finder.find_path(g, "a", "c", all_blocked)


class RecordingFinder:
    """A stand-in PathFinder: proves the router delegates the search."""

    def __init__(self):
        self.calls = 0

    def find_path(self, graph, source, target, cost):
        self.calls += 1
        return NetworkXDijkstra().find_path(graph, source, target, cost)


def test_router_uses_injected_path_finder_and_cost():
    finder = RecordingFinder()
    router = Router(square(), path_finder=finder)
    route = router.route(Point(0, 0), Point(100, 0), cost=lambda u, v, d: d["length_m"])
    assert finder.calls == 1
    assert route.length_m == pytest.approx(100)  # plain length ignores the cost_factor
    assert router.route(Point(0, 0), Point(100, 0)).length_m == pytest.approx(300)  # default walking cost


def test_no_hazard_means_every_edge_is_dry():
    snap = NoHazard().snapshot(square())
    assert snap.condition("e0") == DRY and snap.source == "none"


def test_snapshot_without_an_entry_falls_back_to_its_default():
    snap = HazardSnapshot(source="sensor", conditions={"e1": EdgeCondition(depth_m=0.12)})
    assert snap.condition("e1").depth_m == 0.12
    assert snap.condition("e2") == UNKNOWN and not snap.condition("e2").is_known
