import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, box

from floodroute.network import PARCEL_ACCESS, com_builder
from floodroute.routing import Router, RoutingError

CRS = "EPSG:7855"


def grid_graph(study_area=None, points=(), extra_lines=()):
    """A 2x2-block grid, 100 m blocks, nodes at (0..200, 0..200)."""
    lines = list(extra_lines)
    for k in (0, 100, 200):
        lines += [LineString([(0, k), (100, k)]), LineString([(100, k), (200, k)]),
                  LineString([(k, 0), (k, 100)]), LineString([(k, 100), (k, 200)])]
    rows = [{"objectid": str(i), "neworkid": None, "geometry": g} for i, g in enumerate(lines)]
    rows += [{"objectid": f"p{i}", "neworkid": pid, "geometry": Point(xy)} for i, (pid, xy) in enumerate(points)]
    raw = gpd.GeoDataFrame(rows, geometry="geometry", crs=CRS)
    graph, _ = com_builder.build_graph(raw, study_area=study_area, buffer_m=1000)
    return graph


def test_route_between_mid_edge_points():
    router = Router(grid_graph())
    route = router.route(Point(30, 2), Point(170, 198))  # just off two edges
    assert route.origin.distance_m == pytest.approx(2)
    # 2 m access, 70 m to (100,0), 200 m north to (100,200), 70 m east to (170,200), 2 m access
    assert route.length_m == pytest.approx(2 + 70 + 200 + 70 + 2)
    assert route.geometry.coords[0] == pytest.approx((30, 0))
    assert route.geometry.coords[-1] == pytest.approx((170, 200))
    assert route.geometry.length == pytest.approx(route.length_m - 4)


def test_origin_and_destination_on_same_edge():
    router = Router(grid_graph())
    route = router.route(Point(80, 1), Point(20, 1))
    assert route.length_m == pytest.approx(1 + 60 + 1)
    assert route.geometry.coords[0] == pytest.approx((80, 0))
    assert route.geometry.coords[-1] == pytest.approx((20, 0))


def test_same_point_gives_zero_length_route():
    route = Router(grid_graph()).route(Point(50, 0), Point(50, 0))
    assert route.length_m == pytest.approx(0)


def test_point_outside_study_area_is_rejected():
    router = Router(grid_graph(study_area=box(0, 0, 150, 150)))
    with pytest.raises(RoutingError, match="outside"):
        router.route(Point(50, 0), Point(180, 180))


def test_point_too_far_from_network_is_rejected():
    router = Router(grid_graph(), max_snap_m=10)
    with pytest.raises(RoutingError, match="from the nearest footpath"):
        router.route(Point(50, 50), Point(100, 0))


def test_snapping_ignores_parcel_links_and_routes_never_cross_parcels():
    # Parcel P at (10,10) with diagonal links to (50,0) and (0,50): cutting through it would save 17.6 m.
    links = [LineString([(10, 10), (50, 0)]), LineString([(10, 10), (0, 50)])]
    graph = grid_graph(points=[("P", (10, 10))], extra_lines=links)
    router = Router(graph)
    route = router.route(Point(90, 0), Point(0, 90))
    assert route.length_m == pytest.approx(180)  # around the corner, not 162.4 through the parcel
    assert all(graph.nodes[n]["kind"] != PARCEL_ACCESS for n in route.nodes if n in graph)
    # A click right on a parcel link snaps to the nearest street instead.
    snap = router.snap(Point(30, 5))
    assert snap.distance_m == pytest.approx(5)


def test_point_beside_a_bridge_can_join_the_path_underneath():
    # Ground path y=0 from x=0..200. A bridge deck at y=10 crosses over it, only reachable from
    # far away via ramps at x=-300 and x=500. A point at (100, 6) is nearest to the bridge.
    ground = [LineString([(0, 0), (100, 0)]), LineString([(100, 0), (200, 0)])]
    bridge = [LineString([(-300, 10), (500, 10)]),
              LineString([(-300, 10), (-300, -400)]), LineString([(-300, -400), (0, -400)]),
              LineString([(0, -400), (0, 0)]), LineString([(500, 10), (500, -400)]),
              LineString([(500, -400), (200, -400)]), LineString([(200, -400), (200, 0)])]
    rows = [{"objectid": str(i), "neworkid": None, "geometry": g} for i, g in enumerate(ground + bridge)]
    graph, _ = com_builder.build_graph(gpd.GeoDataFrame(rows, geometry="geometry", crs=CRS))
    router = Router(graph)
    assert router.snap(Point(100, 6)).distance_m == pytest.approx(4)  # the bridge is nearest
    route = router.route(Point(100, 6), Point(150, 0))
    assert route.length_m == pytest.approx(6 + 50)  # but the route joins the ground path


def test_carriageway_penalty_prefers_sidewalk():
    # Two parallel ways between the same corners: a 100 m carriageway and a 110 m sidewalk.
    road = LineString([(0, 0), (100, 0)])
    sidewalk = LineString([(0, 0), (0, 5), (100, 5), (100, 0)])
    rows = [{"objectid": "r", "neworkid": None, "geometry": road},
            {"objectid": "s", "neworkid": None, "geometry": sidewalk}]
    graph, _ = com_builder.build_graph(gpd.GeoDataFrame(rows, geometry="geometry", crs=CRS))
    for *_, d in graph.edges(data=True):
        d["cost_factor"] = 3.0 if d["objectid"] == "r" else 1.0
    route = Router(graph).route(Point(0, 0), Point(100, 0))
    assert route.length_m == pytest.approx(110)
