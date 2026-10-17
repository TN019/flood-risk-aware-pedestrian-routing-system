# Architecture

Every number used below is listed with its source or reason in [parameters.md](parameters.md).

## Layers

The `floodroute` package is organised bottom-up. Each layer depends only on the layers below it.

```
sources     external data: OpenStreetMap, City of Melbourne (incl. stormwater pits), Nominatim
            place search, Geoscience Australia elevation, Vicmap Planning flood overlays
network     routing graph construction, schema, storage
hazard      flood conditions on network edges        ── HazardProvider
risk        edge costs and impassable edges          ── EdgeCost
routing     snapping, cheapest and safest-path search ── PathFinder
places      where a walk starts and ends (building entrances), refuges
trip        whole-trip planning: routes, downgrade, refuge, emergency
prediction  forecasting models                       ── Predictor
```

A web API (FastAPI) and the web client sit on top of these layers; neither contains routing logic.

## Web API and client

`floodroute.api` serves the engine over HTTP. `api.service.Service` loads the network, places,
refuges and scenarios once and answers in WGS84 GeoJSON; `api.app` maps it onto routes:

| Route | Returns |
|---|---|
| `GET /api/area` | study area, routable area (with its margin) and bounds |
| `GET /api/network` | walking network for display: paths, margin paths, avoided carriageways |
| `GET /api/options` | body-part limits, landmarks, route preferences, flood levels, SOS undo window |
| `GET /api/scenarios` | scenarios with their level, typical depth, description and sources |
| `GET /api/scenarios/{id}/water` | wet and unknown-depth edges of a scenario |
| `GET /api/search?q=` | place search inside the routable area (Nominatim, cached, one request a second) |
| `POST /api/traveller` | a traveller's depth limit and what their preference means in metres |
| `POST /api/trip` | the whole trip plan: where they stand, three routes, least water, downgrade, refuge, emergency |

Start and destination must lie inside the study area; requests that cannot be answered as asked
return 422 with a message for the user. The web client (`frontend/`, React, TypeScript and
MapLibre on an OpenStreetMap basemap) keeps no routing rules of its own: it shows what the API
returns, with the map and a side panel on desktops and the map above a sliding sheet on phones.
Sending an SOS is simulated in the client, with a short window to undo it.

The results open with a **next step** card that turns the plan into one instruction
(`frontend/src/guidance.ts`, unit-tested):

| Situation | Next step | Highlighted on the map |
|---|---|---|
| a route fits and it is the shortest way | go, with distance, time and deepest water | recommended |
| a route fits, but it detours | take the recommended route, and what the detour avoids | recommended |
| no route fits; a higher limit or a shelter (or staying inside) would work | the two choices side by side | neither until one is picked |
| no route fits; only a higher limit works | accept deeper water, with a button to use that limit | the higher-limit route |
| no route fits; only a shelter is reachable | go to the shelter and wait (folded under "if you cannot wait" when the start is critical) | the shelter route |
| no route fits and the traveller is indoors | stay inside | the least-water route |
| no route and no shelter | call for help; stay on high ground | the least-water route |

Whenever no route fits, the card says why: the least water any way to the destination has to
cross, against the traveller's limit or the 50 cm hard limit, with that point marked on the map.
Picking a choice, or a row under "Compare routes", highlights its route, dims the others and zooms
to it; every route has a white outline so it stays readable above the water. The legend lists only
what is on the map, and starts folded on phones.

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
| `HazardProvider.snapshot(graph, at)` → `HazardSnapshot` | `hazard` | `NoHazard`; `GridHazard` (depth grids of the scenarios in `data/scenarios/`); `ScenarioHazard` (hand-drawn zones) | real-time sensors, model forecasts per time horizon |
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

A traveller picks the deepest water they accept as a body part; `risk.profile.TravellerProfile`
converts it to a depth from their height H, capped at 50 cm:

| Choice | Depth | 170 cm adult |
|---|---|---|
| No wading | 2 cm | 2 cm |
| Ankle | 0.039 × H | 6.6 cm |
| Lower calf | 0.121 × H | 20.6 cm |
| Mid calf | 0.162 × H | 27.5 cm |
| Knee | 0.285 × H | 48.5 cm |

Ankle and knee heights are Drillis & Contini's body proportions; the calf points lie a third of
the way and halfway from ankle to knee. The 50 cm cap is Melbourne Water's limit for safe
pedestrian access in Southbank, and the H2 depth limit for people (Smith, Davey & Cox, 2014); it
binds only for the knee, for people taller than about 175 cm. Thigh and waist are not offered:
they would read 50 cm for almost everyone. Wheelchair users are limited to 2 cm. Up to 2 cm counts as dry
pavement for everyone, so "no wading" means no water beyond what any pavement carries in rain.

`risk.model.DepthRelativeRisk` gives each edge a risk from its deepest point:

- ≤ 2 cm: R = 0 (dry); above the traveller's limit, or unknown depth: impassable
- otherwise R = depth ÷ limit, so R = 1 is "right at your limit"

and `risk_cost` turns it into the routing cost

    cost = cost_factor × (dry length + wet length × (1 + α·R)),   α = 2 by default

where wet length is the part of the edge deeper than 2 cm, R comes from the edge's deepest point,
and `cost_factor` is 3 for walking along a carriageway that has a sidewalk alongside, 1 otherwise.

With no water R = 0 everywhere and the cost equals the plain walking cost, so routes without a
flood are identical to routing without the risk layer (tested on the Southbank network). Flow
velocity is not used yet.

### Wheelchair users

Wheelchair users get two rules: water no deeper than 2 cm, and **no steps**. `risk.access.can_use`
makes an edge with `is_steps` (OSM `highway=steps`, 100 network edges) impassable for them,
whatever the water, and every search made for them applies it: `risk_cost` (shortest within limit,
recommended, refuge), `walking_cost_for` (shortest ignoring flooding, least water, safest way to a
refuge) and the depth used by the minimax search. So their "shortest" is the shortest step-free
way, a refuge whose entrances can only be reached by steps is not offered, and the least water is
the least over step-free ways. For everyone else steps are ordinary paths, and nothing changes.

The straight access leg from a point to a footpath could otherwise skip a short flight: from the
bottom of a 6 m flight, the footpath at its top is within the 15 m snapping reach. So the router
marks an access leg as steps when it runs alongside or across the middle of a flight (within
0.5 m of it, leaving out a metre at each end where legs may meet it) or passes within a metre of
both its ends (a flight that turns back on itself; one in Southbank has its ends 2 m apart).
Level changes not mapped as steps, such as a footpath on a deck just above, are not known and can
still be bridged by an access leg, for every traveller.

Each route reports whether it uses steps, access legs included (`Route.uses_steps`, `uses_steps` in the API), and the
plan reports `step_free` and `steps_avoided` (the plain shortest way has steps that the routes
avoid). When no step-free way connects the two places at all, every option carries the error "No
step-free route connects these places."

Steep paths are **not** filtered yet. The intended rule is a gradient steeper than 1:14 (AS 1428.1's
steepest ramp; see [parameters.md](parameters.md)), but OSM's `incline` tag in Southbank never gives
a gradient: it is set on 2.6% of the raw network edges, always as `up`, `down` or `yes`, and mostly on steps.
The processed network therefore does not keep it. Kerbs, ways tagged `wheelchair=no` and surface
are not used either.

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

### Flood levels

Flood levels are defined by how deep the water is on an adult (`risk.levels`). A scenario's level
comes from its typical depth: the median depth, weighted by length, of the water on flooded
footpaths inside Southbank.

| Level | Typical depth | Reference adult (1.70 m) |
|---|---|---|
| Light | up to the ankle | up to 6.6 cm |
| Moderate | over the calf, up to the knee | 6.6–48.5 cm |
| Heavy | over the thigh, up to the hip | 48.5–90.1 cm |
| Extreme | above the hip | over 90.1 cm |

Ankle, knee and hip are the waterlines used to grade flood severity from photographs of people
(Feng, Brenner & Sester, 2020), placed at Drillis & Contini's proportions of stature (0.039, 0.285,
0.530). The reference height is the Australian adult average, 1.69 m (ABS Australian Health Survey
2011–12), rounded. The knee boundary also matches where hazard guidance draws its first limits for
people: 0.5 m is the H2 depth limit and the most children can wade (Smith, Davey & Cox, 2014), and
Melbourne Water's limit for safe pedestrian access in Southbank.

### Flood scenarios

Each bundled scenario is a JSON definition in `data/scenarios/` (`hazard.catalog`) that names the
level it stands for, the event behind it, its parameters and their sources;
`scripts/make_scenarios.py` turns it into a water-depth grid in `data/processed/scenarios/` and
fails if the grid's typical depth falls outside the stated level. `hazard.grid.GridHazard` samples a
grid every 2 m along each edge: the edge gets its deepest sampled depth and its wet length; an edge
crossing a cell without data gets an unknown depth; bridges are dry, since a bare-earth model shows
the ground under the deck.

Each level is a published event, not a tuned water level:

| Level | Event | Tide (m AHD) | Ponding | Typical depth |
|---|---|---|---|---|
| 0 Normal | — | — | — | — |
| 1 Light | heavy rain at the highest normal tide | 0.59 | a quarter full | 6 cm |
| 2 Moderate | 1-in-20-year storm tide with heavy rain | 1.25 | full | 32 cm |
| 3 Heavy | 1-in-100-year storm tide today, with heavy rain | 1.60 | full | 54 cm |
| 4 Extreme | the same in 2100, with 0.8 m of sea level rise | 2.40 | full | 99 cm |

Tide levels: highest astronomical tide at Williamstown from the Port Phillip Bay Coastal Hazard
Assessment (2023); storm tides from GHD for Melbourne Water (2017), Table 1. 1.60 m is also the
major flood level at the VICSES Southbank gauge, and the 0.8 m allowance is Victoria Planning
Provisions clause 13.01-2S.

Depths follow the flood mechanisms in Melbourne Water's Southbank Precinct Local Floodplain
Development Plan (2026) and the City of Melbourne flood and storm emergency sub-plan (2025),
estimated on the Geoscience Australia 5 m LiDAR elevation model (`hazard.terrain`):

- **River and storm tide.** Water at the tide level reaches every ground cell below it that is
  connected to the river through lower ground; low ground behind higher ground stays dry.
- **Drain backflow.** A high tide stops the drains discharging and water comes back up around the
  drainage pits. Every surface inlet (grated, side-entry and lane pits; City of Melbourne
  stormwater pits open data) on ground below the tide level lets the tide in as well, so low
  ground cut off from the river overland floods through the drains.
- **Stormwater ponding.** Rain the drains cannot take collects in closed depressions of the
  terrain, wherever they are; `ponding_fill_fraction` sets how far each fills from its lowest point
  towards its spill point.

How a depth grid is computed, cell by cell on the 5 m grid:

1. **Walking surface.** River and dock cells (flattened to 0 m AHD in the ground model) take the
   elevation of the nearest bank, so paths along the water do not read the river surface. Pits more
   than 0.5 m below the median of their 25 m neighbourhood (basement ramps, road cuttings) are
   raised to 0.5 m below it. A 3 × 3 median then removes single-cell noise.
2. **Tide.** Starting from the river cells and from the cells holding a drain inlet, water spreads
   to every neighbouring cell (including diagonals) whose ground is below the tide level, and on
   from there. Depth = tide level − ground.
3. **Ponding.** For every cell, the spill elevation is the lowest level water there would have to
   rise to before it could flow, cell by cell, to the river or the edge of the grid (found by
   priority-flood depression filling). Where it is above the ground the cell lies in a closed
   depression. Each depression has a bottom (its lowest cell) and a rim (its spill elevation); its
   water level is bottom + fill fraction × (rim − bottom), and depth = water level − ground. For a
   depression with its bottom at 1.80 m and its rim at 2.20 m AHD, a quarter fill puts the water at
   1.90 m, 10 cm deep at the bottom; a full one puts it at 2.20 m, 40 cm deep.
4. **Combined.** Each cell takes the deeper of the tide and ponding depths.
5. **Unreliable ground.** Land the highest astronomical tide (0.59 m AHD) reaches overland from the
   river would be flooded by ordinary tides; in Southbank these cells are excavations and filled
   voids in the ground model (e.g. at Freshwater Place). Their depth is left unknown in every
   scenario, so routes avoid them as they do any water of unknown depth (17 footpath sections,
   1.2% of the network).
6. **On the network.** `GridHazard` reads the depth every 2 m along each edge, as described above.

Which parts rest on a source and which are chosen:

- From sources: the ground model, the drain inlets, the mechanisms, the tide levels, the level
  boundaries and the reference height.
- Chosen: the quarter fill for light flooding (there is no published depth for local ponding in
  Southbank; a half fill would give about 10 cm, above the ankle), the pit rule, the smoothing and the
  2 m sampling.

Checks against results the method was not fitted to:

- VICSES's Southbank Local Flood Guide (2021) expects 300 mm or more on Whiteman, Clarendon,
  Kings, Moray, Clarke and Catherine streets, Haig Lane and City Road at 1.2 m on the Southbank
  gauge. At a 1.2 m tide the grids give 43–68 cm on all of them. The guide does not state the
  gauge's datum; the comparison assumes it is close to AHD.
- The floodplain plan describes river water filling a low area around Clarke Street between City
  Road and Haig Lane; Clarke Street and Haig Lane are the deepest of the streets above at every
  level (10, 73, 108 and 188 cm at levels 1–4).

Limits:

- A static estimate, not a hydraulic model: no flow, velocity, timing or pipe capacity. Water fills
  every depression even where a drain would empty it, and drain backflow reaches the tide level at
  every inlet below it, with no head from rain in the pipes.
- Without that head, rain-driven surcharge at a normal tide is missed. On 26 October 2025 a
  short storm (15 mm in 15 minutes, Bureau of Meteorology) at a predicted high tide of about
  0.42 m AHD left more than half a metre on Whiteman Street, by a resident's account; light
  flooding leaves Whiteman Street dry (its lowest ground is 0.79 m AHD). Pit and pipe levels
  are not published, so the head cannot be modelled yet.
- River levels are the bay's tide levels; river flows can raise Southbank levels above them, so
  river depths are a lower bound.
- 5 m cells cannot show kerbs and gutters, where real ponding often sits, and buildings are
  removed from a bare-earth model, so water can spread across ground a building occupies.
- Raising pits can hide water in a genuine pedestrian underpass.

A hydraulic model's depth grid (e.g. a TUFLOW run) can replace this estimate through the same
`GridHazard`.

Share of the Southbank network under water, deepest water on it, and share of 150 random trips
with a route within the limit of a 170 cm adult (unknown-depth sections, 1.2% of the network in
every flooded scenario, are impassable):

| Level | Network wet | Deepest | No wading | Ankle | Lower calf | Mid calf |
|---|---|---|---|---|---|---|
| 0 Normal | 0% | — | 100% | 100% | 100% | 100% |
| 1 Light | 1.4% | 14 cm | 85% | 93% | 95% | 95% |
| 2 Moderate | 25% | 73 cm | 15% | 20% | 37% | 43% |
| 3 Heavy | 38% | 1.1 m | 13% | 17% | 25% | 27% |
| 4 Extreme | 68% | 1.9 m | 5% | 5% | 5% | 6% |

`hazard.scenarios` (hand-drawn GeoJSON zones with a depth ramp) remains for tests and what-if
experiments.

## Planning a walk

`routing.planning.plan_routes` returns three routes so the effect of each rule is visible:

| Option | Cost | Shows |
|---|---|---|
| `shortest` | walking cost, flood ignored | what an ordinary navigation app would suggest, and its exposure |
| `safe_shortest` | risk cost with α = 0 (safety filter only) | what excluding water over the limit changes |
| `recommended` | risk cost with α (default 2) | what weighting the remaining water changes |

When water is the obstacle, the safe and recommended options carry an error instead of a route;
the shortest option is still returned so the exposure it would involve can be shown. For
wheelchair users all three leave out steps.

## When no safe route exists

`trip.plan_trip` wraps `plan_routes` with what to do when the traveller cannot stay within their
limit, or is already standing in water over it.

**Where the traveller stands.** The depth at the start is judged against their own body
(`risk.alerts`): at a corner where several footpaths meet they stand on the shallowest. Starting
inside a building counts as sheltered.

| Level | Water at the start | What is offered |
|---|---|---|
| `OK` | within their limit | normal routes |
| `OVER_LIMIT` | over their limit, up to 50 cm | warning; refuge and downgrade if no safe route |
| `DEEP` | over 50 cm (below the knee only for people taller than about 175 cm) | refuge (safest route); emergency help available |
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

**Least water.** When the destination is out of reach within the limit, the safest-path search gives
the way that faces the least water (`trip.find_least_water`): how deep its deepest point is, where
that point is, and the route. It is reported whatever the depth, so the traveller can see why no
route fits.

**Downgrade.** From the least water, the smallest body part covering it (never above 50 cm, never
for wheelchair users) is offered with that route. For wheelchair users the least water and the
refuge route are searched over step-free ways only.

**Refuges.** In this version every building with a way in counts as a sheltered refuge
(`places.refuges`); whether it is open to the public is not known from the data. The nearest 25
buildings within 800 m in a straight line are tried; beyond that, emergency help is offered instead. From dry ground
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
