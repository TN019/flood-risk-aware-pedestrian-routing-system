import geopandas as gpd
import networkx as nx
import pytest
from shapely.geometry import LineString, Point, box

import places as pl
from routing import Router

CRS = "EPSG:7855"


def gdf(rows):
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=CRS)


def street_graph():
    """A street along y=0 (x 0..300) and one along x=300 (y 0..200). Building sits at x 100..200, y 10..60."""
    g = nx.Graph(crs=CRS)
    for n, (x, y) in {1: (0, 0), 2: (150, 0), 3: (300, 0), 4: (300, 200)}.items():
        g.add_node(n, x=x, y=y, kind="junction", parcel_id=None, in_study_area=True)
    for i, (u, v) in enumerate(((1, 2), (2, 3), (3, 4))):
        geom = LineString([(g.nodes[u]["x"], g.nodes[u]["y"]), (g.nodes[v]["x"], g.nodes[v]["y"])])
        g.add_edge(u, v, geometry=geom, length_m=geom.length, edge_id=f"e{i}", cost_factor=1.0)
    return g


BUILDING = box(100, 10, 200, 60)
NESTED = box(120, 20, 140, 40)  # a smaller building part inside the main one


def resolver(entrances=()):
    buildings = gdf([{"name": "Big", "geometry": BUILDING}, {"name": None, "geometry": NESTED},
                     {"name": "Far", "geometry": box(1000, 1000, 1010, 1010)}])
    ents = gdf([{"element": "node", "id": i, **e} for i, e in enumerate(entrances)]) if entrances else \
        gdf([{"element": "node", "id": 0, "entrance": "yes", "geometry": Point(5000, 5000)}])
    return pl.PlaceResolver(buildings, ents, Router(street_graph()).footpaths)


def test_point_outside_buildings_stays_a_point():
    place = resolver().resolve(Point(50, -5), "here")
    assert place.method == "point" and place.access_points == [Point(50, -5)]


def test_most_specific_building_is_used():
    building, _ = resolver().building_at(Point(130, 30))
    assert building.equals(NESTED)
    building, name = resolver().building_at(Point(180, 50))
    assert building.equals(BUILDING) and name == "Big"


def test_only_usable_outdoor_entrances_are_kept():
    entrances = [
        {"entrance": "main", "geometry": Point(150, 10)},  # on the outline: kept
        {"entrance": "yes", "geometry": Point(200, 30)},  # on the outline: kept
        {"entrance": "emergency", "geometry": Point(110, 10)},
        {"entrance": "service", "geometry": Point(120, 10)},
        {"entrance": "yes", "access": "private", "geometry": Point(130, 10)},
        {"entrance": "yes", "level": "1", "geometry": Point(140, 10)},
        {"entrance": "yes", "indoor_only": True, "geometry": Point(160, 10)},
        {"entrance": "yes", "geometry": Point(150, 35)},  # inside the building, not on its outline
    ]
    place = resolver(entrances).resolve(Point(180, 50), "Big")
    assert place.method == "entrances"
    assert sorted((a.point.x, a.point.y) for a in place.access) == [(150, 10), (200, 30)]
    assert place.access_label(Point(150, 10)) == "main entrance"


def test_exit_only_door_can_be_left_but_not_entered():
    entrances = [{"entrance": "exit", "geometry": Point(150, 10)}]
    r = resolver(entrances)
    assert r.resolve(Point(180, 50), "Big", role=pl.ORIGIN).method == "entrances"
    assert r.resolve(Point(180, 50), "Big", role=pl.DESTINATION).method == "outline"


def test_outline_fallback_uses_edges_nearest_the_footpaths():
    place = resolver().resolve(Point(180, 50), "Big")
    assert place.method == "outline"
    first = place.access[0].point
    assert first.y == pytest.approx(10)  # the south wall faces the street at y=0
    pts = place.access_points
    assert all(a.distance(b) >= pl.OUTLINE_POINT_SPACING_M for i, a in enumerate(pts) for b in pts[i + 1:])


def test_footprint_selects_buildings_inside_it():
    footprint = box(90, 0, 210, 70)
    building, _ = resolver().building_at(Point(0, 0), footprint)
    assert building.covers(BUILDING) and building.covers(NESTED)


def test_router_picks_the_cheapest_entrance():
    router = Router(street_graph())
    # Entrance A faces the y=0 street at x=150; entrance B faces the x=300 street, 100 m further on.
    a, b = Point(150, 10), Point(200, 30)
    route = router.route(Point(0, 0), [a, b])
    assert route.destination.point.equals(a)
    assert route.length_m == pytest.approx(150 + 10)
