# Parameters and their basis

Every number that changes a route, a depth or an alert, with where it is set and why it has its
value. [architecture.md](architecture.md) describes how the numbers are used.

Basis:

- **Cited**: taken from a named source.
- **Derived**: worked out from cited values; the working is given.
- **Measured**: read from the data.
- **Chosen**: a judgement, with the reason. These are the first values to revisit when better
  evidence is available.

## Traveller

| Parameter | Value | Where | Basis |
|---|---|---|---|
| Ankle height | 0.039 × height | `risk.profile.BodyPart` | Cited: Drillis & Contini (1966) body segment proportions |
| Knee, hip, chest, shoulder heights | 0.285, 0.53, 0.72, 0.818 × height | `risk.profile.LANDMARKS` | Cited: Drillis & Contini (1966) |
| Lower calf height | 0.121 × height | `risk.profile.BodyPart` | Derived: a third of the way from ankle to knee, 0.039 + (0.285 − 0.039) / 3 |
| Mid calf height | 0.162 × height | `risk.profile.BodyPart` | Derived: halfway between ankle and knee |
| Mid thigh, waist heights | 0.41, 0.63 × height | `risk.profile.LANDMARKS` | Derived: about halfway knee–hip and hip–chest; used only to describe a depth |
| Hard limit | 30 cm | `risk.profile.HARD_LIMIT_M` | Chosen: nobody is routed through deeper water whatever their height or choice. For comparison, Melbourne Water's Southbank plan takes up to 500 mm as safe pedestrian access, and up to 300 mm for vulnerable uses |
| No-wading limit, wheelchair limit, dry pavement | 2 cm | `hazard.base.DRY_DEPTH_M` | Chosen: a film of water any pavement carries in rain. Water up to 2 cm costs nothing; deeper water counts as wading. "Knee" is not offered as a limit: at 0.285 × height it exceeds 30 cm for anyone taller than about 105 cm |
| Accepted heights | 0.5–2.5 m | `risk.profile.TravellerProfile` | Chosen: input check |
| Walking speed | 1.3 m/s | `risk.profile.DEFAULT_WALKING_SPEED_M_S` | Chosen: a typical adult pace; only used for travel times |

## Alerts at the start

| Parameter | Value | Where | Basis |
|---|---|---|---|
| Deep | over 30 cm | `risk.alerts` | The hard limit |
| Very deep | above the knee, 0.285 × height | `risk.alerts.KNEE_FRACTION` | Cited proportion; chosen as the point where walking out is no longer advised without help |
| Critical | above half the height, or unknown depth | `risk.alerts.HALF_HEIGHT_FRACTION` | Chosen: at half a person's height the water lifts enough of their weight that they can lose their footing even in still water; unknown depth is treated as the worst case |

## Route cost

| Parameter | Value | Where | Basis |
|---|---|---|---|
| Risk weight α per preference | 0.5, 2, 5, 15 | `risk.preference.RoutePreference` | Chosen: α is the extra metres worth walking to avoid one metre of water right at the limit. Spaced 2.5–4 times apart so each preference is distinct; the app explains each in metres |
| Default preference | Balanced, α = 2 | `risk.preference.DEFAULT_PREFERENCE` | Chosen |
| Example in the explanation | 50 m of water at 75% of the limit | `risk.preference` | Chosen: only for the sentence shown to the traveller |
| Carriageway with a sidewalk alongside | cost × 3 | `network.osm_builder.CARRIAGEWAY_PENALTY` | Chosen: high enough that routes keep to the sidewalk and only cross the road, low enough that a carriageway is still usable where it is the only way |
| "Sidewalk alongside" | within 20 m along 80% of the carriageway | `network.osm_builder` | Chosen: Melbourne's OSM data rarely tags `sidewalk=separate`, so it is decided geometrically |

## Network and snapping

| Parameter | Value | Where | Basis |
|---|---|---|---|
| Network beyond the study area | 250 m | `config.STUDY_AREA_BUFFER_M` | Chosen: room for detours and river crossings near the boundary |
| Furthest point from a footpath | 100 m | `routing.router.MAX_SNAP_DISTANCE_M` | Chosen: further away is treated as not on the walking network |
| Footpaths also considered | up to 15 m further than the nearest | `routing.router.SNAP_SLACK_M` | Chosen: the nearest line may be a bridge deck above the path the person is actually on |
| Footpaths counted as "standing on" | within 1 m of the nearest | `routing.router.STANDING_TOLERANCE_M` | Chosen: at a corner the traveller stands on the shallowest of these |
| Entrance belongs to a building | within 1.5 m of its outline | `places.resolver` | Chosen: OSM entrance nodes sit on or next to the outline |
| Building without mapped entrances | outline points nearest the footpaths within 60 m, at least 15 m apart | `places.resolver` | Chosen |
| Access points per place | at most 8 | `places.resolver.MAX_ACCESS_POINTS` | Chosen: bounds the search |
| Refuge search | 800 m straight line, nearest 25 buildings | `places.refuges` | Chosen: about ten minutes' walk; beyond it, emergency help is offered instead |

## Flood scenarios

| Parameter | Value | Where | Basis |
|---|---|---|---|
| Ground model | 5 m cells, metres AHD | `sources.terrain` | Cited: Geoscience Australia 5 m LiDAR DEM (2025) |
| Two flood mechanisms | river and storm tide; local stormwater | `hazard.terrain` | Cited: Melbourne Water, Southbank Precinct Local Floodplain Development Plan (2026) |
| River levels | 1.6, 1.8, 2.4 m AHD | `data/scenarios/*.json` | Cited: Melbourne Water 1% AEP tide levels for Port Phillip Bay today, 2040 and 2100 (Planning for Sea Level Rise Guidelines, 2017, as cited by GHD, 2019) |
| Sea level rise to 2100 | 0.8 m | included in 2.4 m | Cited: Victoria Planning Provisions clause 13.01-2S |
| Stormwater ponding fill | a quarter (light), full (levels 2–4) | `data/scenarios/*.json` | Chosen: no published depth for local ponding in Southbank. A quarter keeps light ponding shallow (14 cm at most on the network); full is the most a depression holds before it overflows |
| River and dock surface | ground at or below 0.05 m AHD | `hazard.terrain.WATER_SURFACE_M` | Measured: the ground model flattens river and dock surfaces to 0 m AHD (17,324 of the 20,150 cells at or below this level are exactly 0) |
| Pits lifted | more than 0.5 m below the median of a 25 m window | `hazard.terrain` | Chosen: removes basement ramps and cuttings, which would otherwise read as metres of water beside a footpath |
| Ground smoothing | 3 × 3 cell median | `hazard.terrain.GROUND_FILTER_CELLS` | Chosen: removes single-cell noise |
| Sampling along an edge | every 2 m | `hazard.grid.SAMPLE_SPACING_M` | Chosen: finer than the 5 m cells, so no cell an edge crosses is skipped |
