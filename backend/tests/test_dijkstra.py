import random

import networkx as nx
import pytest

from floodroute import config
from floodroute.risk import walking_cost
from floodroute.routing import Dijkstra, NetworkXDijkstra, NoPathError

LENGTH = lambda u, v, d: d["length_m"]  # noqa: E731


def graph(edges):
    g = nx.Graph()
    for u, v, w in edges:
        g.add_edge(u, v, length_m=w)
    return g


def path_cost(g, path, cost):
    return sum(cost(u, v, g.edges[u, v]) for u, v in zip(path, path[1:]))


def test_picks_the_cheaper_of_two_routes():
    g = graph([("a", "b", 1), ("b", "d", 1), ("a", "c", 1), ("c", "d", 5)])
    result = Dijkstra().search(g, "a", "d", LENGTH)
    assert result.path == ["a", "b", "d"] and result.cost == 2


def test_more_hops_can_be_cheaper():
    g = graph([("a", "d", 10), ("a", "b", 1), ("b", "c", 1), ("c", "d", 1)])
    assert Dijkstra().find_path(g, "a", "d", LENGTH) == ["a", "b", "c", "d"]


def test_source_equals_target():
    g = graph([("a", "b", 1)])
    result = Dijkstra().search(g, "a", "a", LENGTH)
    assert result.path == ["a"] and result.cost == 0


def test_impassable_edges_are_skipped():
    g = graph([("a", "b", 1), ("b", "d", 1), ("a", "c", 2), ("c", "d", 2)])
    no_b = lambda u, v, d: None if "b" in (u, v) else d["length_m"]  # noqa: E731
    assert Dijkstra().find_path(g, "a", "d", no_b) == ["a", "c", "d"]


def test_no_path_raises():
    g = graph([("a", "b", 1), ("c", "d", 1)])
    with pytest.raises(NoPathError):
        Dijkstra().find_path(g, "a", "d", LENGTH)
    with pytest.raises(NoPathError):
        Dijkstra().find_path(g, "a", "missing", LENGTH)
    with pytest.raises(NoPathError):
        Dijkstra().find_path(g, "a", "b", lambda u, v, d: None)


def test_negative_cost_is_rejected():
    g = graph([("a", "b", -1)])
    with pytest.raises(ValueError, match="negative"):
        Dijkstra().find_path(g, "a", "b", LENGTH)


def test_zero_cost_edges_are_fine():
    g = graph([("a", "b", 0), ("b", "c", 0), ("a", "c", 1)])
    assert Dijkstra().search(g, "a", "c", LENGTH).cost == 0


def test_stops_once_target_is_settled():
    # A long tail beyond the target should not be explored.
    g = graph([("s", "t", 1)] + [(f"x{i}", f"x{i + 1}", 1) for i in range(100)] + [("s", "x0", 5)])
    result = Dijkstra().search(g, "s", "t", LENGTH)
    assert result.settled == 2


@pytest.mark.parametrize("seed", range(40))
def test_matches_networkx_on_random_graphs(seed):
    rng = random.Random(seed)
    g = nx.gnm_random_graph(60, 140, seed=seed)
    for u, v in g.edges:
        g.edges[u, v]["length_m"] = rng.choice([0.0, rng.uniform(0.1, 100)])
        g.edges[u, v]["cost_factor"] = rng.choice([1.0, 1.0, 3.0])
    blocked = {e for e in g.edges if rng.random() < 0.1}
    cost = lambda u, v, d: None if (u, v) in blocked or (v, u) in blocked else walking_cost(u, v, d)  # noqa: E731
    ours, reference = Dijkstra(), NetworkXDijkstra()
    for _ in range(25):
        s, t = rng.randrange(60), rng.randrange(60)
        try:
            expected = path_cost(g, reference.find_path(g, s, t, cost), cost)
        except NoPathError:
            with pytest.raises(NoPathError):
                ours.find_path(g, s, t, cost)
            continue
        result = ours.search(g, s, t, cost)
        assert result.path[0] == s and result.path[-1] == t
        assert all(g.has_edge(a, b) and cost(a, b, g.edges[a, b]) is not None for a, b in zip(result.path, result.path[1:]))
        assert path_cost(g, result.path, cost) == pytest.approx(result.cost)
        assert result.cost == pytest.approx(expected)


@pytest.mark.skipif(not config.PROCESSED_NETWORK_PATH.exists(), reason="processed network not built")
def test_matches_networkx_on_the_southbank_network():
    from floodroute.network import load_graph

    g = load_graph(config.PROCESSED_NETWORK_PATH)
    nodes = list(g.nodes)
    rng = random.Random(1)
    ours, reference = Dijkstra(), NetworkXDijkstra()
    for _ in range(200):
        s, t = rng.sample(nodes, 2)
        expected = path_cost(g, reference.find_path(g, s, t, walking_cost), walking_cost)
        assert ours.search(g, s, t, walking_cost).cost == pytest.approx(expected, abs=1e-6)
