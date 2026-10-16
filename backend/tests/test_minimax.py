import itertools
import math
import random

import networkx as nx
import pytest

from floodroute.routing.minimax import MinimaxPathFinder, bottleneck_depth
from floodroute.routing.pathfinding import NoPathError

LENGTH = lambda u, v, d: d["length_m"]  # noqa: E731
DEPTH = lambda u, v, d: d["depth"]  # noqa: E731


def graph(edges):
    g = nx.Graph()
    for u, v, length, depth in edges:
        g.add_edge(u, v, length_m=length, depth=depth)
    return g


def test_prefers_shallower_water_over_shorter_distance():
    # Direct: 100 m through 40 cm. Detour: 300 m through 10 cm.
    g = graph([("a", "b", 100, 0.40), ("a", "c", 150, 0.10), ("c", "b", 150, 0.0)])
    finder = MinimaxPathFinder(DEPTH)
    assert finder.find_path(g, "a", "b", LENGTH) == ["a", "c", "b"]
    assert finder.last_bottleneck_m == pytest.approx(0.10)


def test_among_equally_shallow_paths_takes_the_cheapest():
    g = graph([("a", "b", 100, 0.2), ("b", "d", 100, 0.0), ("a", "c", 50, 0.2), ("c", "d", 60, 0.1)])
    assert MinimaxPathFinder(DEPTH).find_path(g, "a", "d", LENGTH) == ["a", "c", "d"]


def test_two_phases_are_needed():
    # A single (deepest, cost) search would settle d via the cheap 0.1-deep edge first, then lose
    # the cheaper continuation; both prefixes end at 0.3 deep once they take the d-t edge.
    g = graph([("s", "a", 10, 0.1), ("a", "d", 10, 0.1), ("s", "d", 50, 0.0), ("d", "t", 10, 0.3)])
    path = MinimaxPathFinder(DEPTH).find_path(g, "s", "t", LENGTH)
    assert path == ["s", "a", "d", "t"]  # 30 m, not the 60 m via the dry prefix


def test_impassable_and_unknown_depth():
    g = graph([("a", "b", 10, None), ("a", "c", 10, math.inf), ("c", "b", 10, 0.0)])
    depth = lambda u, v, d: d["depth"]  # noqa: E731
    assert bottleneck_depth(g, "a", "b", depth) == math.inf  # only via the unknown edge
    with pytest.raises(NoPathError):
        bottleneck_depth(graph([("a", "b", 10, None)]), "a", "b", DEPTH)


@pytest.mark.parametrize("seed", range(30))
def test_matches_brute_force_on_small_random_graphs(seed):
    rng = random.Random(seed)
    g = nx.gnm_random_graph(9, 16, seed=seed)
    for u, v in g.edges:
        g.edges[u, v]["length_m"] = rng.uniform(1, 100)
        g.edges[u, v]["depth"] = rng.choice([0.0, 0.0, 0.05, 0.1, 0.2, 0.35, 0.6])
    for s, t in [(0, 8), (1, 7), (2, 5)]:
        if not nx.has_path(g, s, t):
            continue
        best = min(
            (
                max(g.edges[a, b]["depth"] for a, b in itertools.pairwise(p)),
                sum(g.edges[a, b]["length_m"] for a, b in itertools.pairwise(p)),
            )
            for p in nx.all_simple_paths(g, s, t)
        )
        finder = MinimaxPathFinder(DEPTH)
        path = finder.find_path(g, s, t, LENGTH)
        deepest = max(g.edges[a, b]["depth"] for a, b in itertools.pairwise(path))
        length = sum(g.edges[a, b]["length_m"] for a, b in itertools.pairwise(path))
        assert (deepest, length) == pytest.approx(best)
        assert finder.last_bottleneck_m == pytest.approx(best[0])
