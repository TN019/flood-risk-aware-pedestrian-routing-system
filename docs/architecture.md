# Architecture

## Layers

The `floodroute` package is organised bottom-up. Each layer depends only on the layers below it.

```
sources     external data: OpenStreetMap, City of Melbourne, Nominatim place search
network     routing graph construction, schema, storage
hazard      flood conditions on network edges        ── HazardProvider
risk        edge costs and impassable edges          ── EdgeCost
routing     snapping, cheapest and safest-path search ── PathFinder
places      where a walk starts and ends (building entrances), refuges
trip        whole-trip planning: routes, downgrade, refuge, emergency
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
| `HazardProvider.snapshot(graph, at)` → `HazardSnapshot` | `hazard` | `NoHazard`; `ScenarioHazard` (synthetic scenarios in `data/scenarios/`) | real-time sensors, model forecasts per time horizon |
| `RiskModel.edge_risk(condition, profile)` → risk or `None` | `risk.model` | `DepthRelativeRisk` (depth ÷ the traveller's limit) | flow velocity (depth × velocity against stability limits), probabilistic models |
| `EdgeCost(u, v, data)` → cost or `None` | `risk` | `walking_cost`; `risk_cost(snapshot, profile, alpha)` | time-dependent costs |
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

## Flood risk

A traveller picks the deepest water they accept as a body part (no wading, ankle, lower calf,
mid calf); `risk.profile.TravellerProfile` converts it to a depth from their height using
anthropometric proportions, capped at 30 cm. Wheelchair users are limited to 2 cm.

`risk.model.DepthRelativeRisk` gives each edge a risk from its deepest point:

- ≤ 2 cm: R = 0 (dry); above the traveller's limit, or unknown depth: impassable
- otherwise R = depth ÷ limit, so R = 1 is "right at your limit"

and `risk_cost` turns it into the routing cost

    cost = cost_factor × (dry length + wet length × (1 + α·R)),   α = 2 by default

With no water R = 0 everywhere and the cost equals the plain walking cost, so routes without a
flood are identical to routing without the risk layer (tested on the Southbank network). Flow
velocity is not used yet.

### Route preferences

Travellers choose a preference rather than a number; each maps to α
(`risk.preference.RoutePreference`):

| Preference | α | Meaning |
|---|---|---|
| Shortest | 0.5 | take the shorter way through water within the limit |
| Balanced (default) | 2 | walk a bit further to stay out of water close to the limit |
| Avoid water | 5 | walk noticeably further to avoid water within the limit |
| Stay as dry as possible | 15 | walk much further, if needed, to keep out of water |

α is the number of extra metres worth walking to avoid one metre of water right at the limit,
scaled down for shallower water. `explain` states it for the traveller in metres, using 50 m of
water at 75% of their limit: for an adult with an ankle limit, Balanced reads "To avoid 50 m of
water 5 cm deep (up to the ankle), you would walk up to about 75 m further." Water over the limit
is never used whatever the preference; for travellers who will not wade the preference has no
effect.

`routing.metrics.route_metrics` reports what a route means for the traveller, separately from the
cost: deepest water and where it reaches on their body, distance in water, depth-weighted
distance in water, sections over their limit, and detour against the shortest route.

### Synthetic scenarios

`hazard.scenarios` reads GeoJSON flood zones (`name`, `max_depth_m`, `ramp_m`); depth rises from
0 at a zone's edge to its maximum `ramp_m` inside it. Each edge gets its deepest sampled depth
and its wet length. Edges outside every zone are dry. Scenarios live in `data/scenarios/`.

`scripts/make_scenarios.py` generates five escalating levels of one illustrative storm; corridors
follow OSM ways by name and the riverfront follows the OSM river polygon. They are synthetic, not
the output of a flood model. Share of the Southbank network under water, and share of 150 random
trips with a route within the limit of a 170 cm adult:

| Level | Network wet | Deepest | No wading | Ankle | Lower calf | Mid calf |
|---|---|---|---|---|---|---|
| 0 Normal | 0% | — | 100% | 100% | 100% | 100% |
| 1 Light ponding | 3% | 5 cm | 96% | 100% | 100% | 100% |
| 2 Moderate flooding | 7% | 25 cm | 92% | 92% | 98% | 100% |
| 3 Severe flooding | 36% | 45 cm | 15% | 16% | 64% | 73% |
| 4 Extreme flooding | 65% | 1 m | 5% | 5% | 8% | 8% |

## Planning a walk

`routing.planning.plan_routes` returns three routes so the effect of each rule is visible:

| Option | Cost | Shows |
|---|---|---|
| `shortest` | walking cost, flood ignored | what an ordinary navigation app would suggest, and its exposure |
| `safe_shortest` | risk cost with α = 0 (safety filter only) | what excluding water over the limit changes |
| `recommended` | risk cost with α (default 2) | what weighting the remaining water changes |

When water is the obstacle, the safe and recommended options carry an error instead of a route;
the shortest option is still returned so the exposure it would involve can be shown.

## When no safe route exists

`trip.plan_trip` wraps `plan_routes` with what to do when the traveller cannot stay within their
limit, or is already standing in water over it.

**Where the traveller stands.** The depth at the start is judged against their own body
(`risk.alerts`): at a corner where several footpaths meet they stand on the shallowest. Starting
inside a building counts as sheltered.

| Level | Water at the start | What is offered |
|---|---|---|
| `OK` | within their limit | normal routes |
| `OVER_LIMIT` | over their limit, up to 30 cm | warning; refuge and downgrade if no safe route |
| `DEEP` | over 30 cm | refuge (safest route); emergency help available |
| `VERY_DEEP` | above the knee (0.285 × height) | refuge; emergency help recommended |
| `CRITICAL` | above half their height, or unknown | emergency help strongly recommended; refuge route only "if you cannot wait" |

If no refuge can be reached at all, emergency help is the only option, with advice to stay on
the highest ground available.

**Safest-path search.** `routing.minimax.MinimaxPathFinder` first finds the lowest possible
"deepest point" over all paths (a bottleneck search: Dijkstra with `max` in place of `+`), then
the cheapest path that never goes deeper. Two phases are needed: a single search on the pair
(deepest so far, cost so far) can discard a prefix that later turns out cheaper. It is checked
against brute-force enumeration of every path on small random graphs. Unknown depth counts as
infinitely deep, used only when nothing else connects.

**Downgrade.** When the destination is out of reach within the limit, the safest-path search gives
the least water that has to be faced; the smallest body part covering it (never above 30 cm, never
for wheelchair users) is offered with that route.

**Refuges.** In this version every building with a way in counts as a sheltered refuge
(`places.refuges`); whether it is open to the public is not known from the data. From dry ground
the route to the nearest refuge stays within the limit; from water over the limit it is the
safest route and is marked as crossing water over the limit.

**Emergency help.** `plan_trip` produces an `SosRequest` (location, depth, how deep that is on the
traveller, their limit, time); sending it, and calling 000, happen in the client.

**Access legs.** The short leg from a point to the footpath it joins also carries the water where
the traveller stands (`standing_on`), so starting from a dry footpath a few metres away does not
hide the water they first have to cross.

## Verifying the path finder

`routing.dijkstra.Dijkstra` is a binary-heap Dijkstra with lazy deletion that stops once the
target is settled. It is checked against NetworkX's implementation, which serves as the
reference:

- `tests/test_dijkstra.py` — hand-made cases (ties, zero-cost and impassable edges, no path,
  negative costs rejected), 40 random graphs × 25 pairs, and 200 pairs on the Southbank network.
- `scripts/compare_pathfinders.py` — 1,000 node pairs and 300 end-to-end routes on the Southbank
  network; every pair must have the same cost. Writes `reports/pathfinder_comparison.md`.
