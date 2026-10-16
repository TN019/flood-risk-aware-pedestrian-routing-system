# Architecture

## Layers

The `floodroute` package is organised bottom-up. Each layer depends only on the layers below it.

```
sources     external data: OpenStreetMap, City of Melbourne, Nominatim place search
network     routing graph construction, schema, storage
hazard      flood conditions on network edges        ── HazardProvider
risk        edge costs and impassable edges          ── EdgeCost
routing     snapping and cheapest-path search        ── PathFinder
places      where a walk starts and ends (building entrances)
prediction  forecasting models                       ── Predictor
```

A web API (FastAPI) and the web client sit on top of these layers; neither contains routing logic.

## Routing graph

`network.schema` documents the graph every source must produce: an undirected `networkx.Graph`
in GDA2020 / MGA zone 55 (EPSG:7855), with `edge_id`, `geometry`, `length_m`, `cost_factor` and
`in_study_area` on every edge.

- **OpenStreetMap (primary)** — `network.osm_builder`. Indoor ways, private ways and carriageways
  tagged `foot=use_sidepath` are excluded. Carriageways with a separately mapped sidewalk alongside
  are kept, because many sidewalks only join the road at junctions, but cost three times their
  length to walk along, so routes use sidewalks and only cross roads where needed. Ways connect
  only at shared OSM nodes, so bridges and underpasses never join the paths they cross.
- **City of Melbourne (alternative)** — `network.com_builder`. A centreline network; property
  parcels are terminal-only so routes cannot cut through them. Kept for comparison: it misses
  footpaths along several arterials (e.g. Kings Way between City Road and Whiteman Street).

The study area is the City of Melbourne CLUE "Southbank" polygon. The graph keeps 250 m of
network beyond it so detours and river crossings work; start and end points must lie inside it.

## Extension points

| Interface | Module | Current implementation | Planned |
|---|---|---|---|
| `HazardProvider.snapshot(graph, at)` → `HazardSnapshot` | `hazard` | `NoHazard` | synthetic flood scenarios, real-time sensors, model forecasts per time horizon |
| `EdgeCost(u, v, data)` → cost or `None` | `risk` | `walking_cost` (length × `cost_factor`) | flood-risk cost and safety filtering from a hazard snapshot and the traveller's depth tolerance |
| `PathFinder.find_path(graph, source, target, cost)` | `routing.pathfinding` | `Dijkstra` (in-house, default); `NetworkXDijkstra` (reference) | A*, time-dependent search |
| `Predictor.fit / predict` | `prediction` | — | linear regression, conditional Markov chains over hazard states, neural networks |

Conventions that keep these interchangeable:

- A cost function returning `None` makes an edge impassable; path finders must honour this.
- A `HazardSnapshot` states its default condition for edges it does not list. Unknown is not dry:
  a provider uses `DRY` as the default only when it knows unlisted edges are dry.
- Forecasting models never talk to routing directly; a provider wraps a model and publishes
  snapshots, so a new model can run alongside the current one before replacing it.

## Routing

`routing.Router` joins arbitrary points to the network and assembles the route:

1. Each endpoint is joined to every footpath within 15 m of its nearest one (bridge deck vs the
   path underneath), via virtual nodes that split the edges.
2. An endpoint may be several access points — `places.PlaceResolver` turns a place inside a
   building into the building's usable outdoor entrances (or the outline points nearest the
   footpaths when no entrance is mapped).
3. The path finder searches from a virtual origin to a virtual destination under the cost
   function; route length includes the short access legs at both ends.

## Verifying the path finder

`routing.dijkstra.Dijkstra` is a binary-heap Dijkstra with lazy deletion that stops once the
target is settled. It is checked against NetworkX's implementation, which serves as the
reference:

- `tests/test_dijkstra.py` — hand-made cases (ties, zero-cost and impassable edges, no path,
  negative costs rejected), 40 random graphs × 25 pairs, and 200 pairs on the Southbank network.
- `scripts/compare_pathfinders.py` — 1,000 node pairs and 300 end-to-end routes on the Southbank
  network; every pair must have the same cost. Writes `reports/pathfinder_comparison.md`.
