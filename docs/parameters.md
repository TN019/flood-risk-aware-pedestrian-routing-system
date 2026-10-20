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
| Knee limit | 0.285 × height | `risk.profile.BodyPart` | Cited: Drillis & Contini (1966); 48.5 cm for a 170 cm adult |
| Mid thigh, waist heights | 0.41, 0.63 × height | `risk.profile.LANDMARKS` | Derived: about halfway knee–hip and hip–chest; used only to describe a depth |
| Hard limit | 50 cm | `risk.profile.HARD_LIMIT_M` | Cited: Melbourne Water's Southbank plan takes up to 500 mm as safe pedestrian access (300 mm for vulnerable uses); 0.5 m is also the H2 depth limit for people (Smith, Davey & Cox, 2014). Nobody is routed through deeper water whatever their height or choice. Thigh and waist are not offered: at 0.41 and 0.63 × height they would be capped to 50 cm for almost everyone |
| No-wading limit, lowest mobility aid level, dry pavement | 2 cm | `hazard.base.DRY_DEPTH_M` | Chosen: a film of water any pavement carries in rain. Water up to 2 cm costs nothing; deeper water counts as wading. Every mobility aid starts at this level ("no water"): manufacturers tell users to avoid standing water (Pride V10 and Pathrider 10 DX owner's manuals; Pride and Quantum wheelchair FAQs) |
| Mobility scooter level and cap | 2.5 cm ("a shallow puddle") | `risk.profile.MobilityAid.MOBILITY_SCOOTER` | Cited: MinnieMobil MM-01/02 owner's manual, "do not pass through water … unless the water is less than 2.5 cm (1 inch) deep", the only depth a manufacturer states. It is below the 3.5 cm motor clearance of a travel scooter (Pride Go-Go Elite Traveller spec sheet). Larger scooters have more clearance (8–10 cm), but the app does not ask for it |
| Manual wheelchair level | 5 cm ("below a 4-inch castor axle") | `risk.profile.MobilityAid.MANUAL_WHEELCHAIR` | Derived: a castor's axle sits at half its diameter, so 5.1 cm for the 4-inch castors in the Quickie Nitrum order form (3–6 inch offered); it also equals the 5 cm kerb limit in Pride's owner's manuals |
| Manual wheelchair cap | 7.5 cm ("below a 6-inch castor axle") | `risk.profile.MobilityAid.MANUAL_WHEELCHAIR` | **Judgement**: the axle of a 6-inch castor (7.6 cm, same derivation). No source sets a wading depth for a manual wheelchair; one mobility blog (Vantage Mobility, 2017, no source given) gives 3 inches |
| Powered wheelchair level and cap | 5 cm ("well below the chassis") | `risk.profile.MobilityAid.POWERED_WHEELCHAIR` | Cited: about 7.5 cm ground clearance (Quickie Q500 M brochure, 3 inches; Permobil M3 Corpus, 75 mm from retailers), and electrics tested only for spray (Invacare Storm⁴ manual, IPX4 under EN 60529). **Judgement**: the 2.5 cm margin below the clearance |
| Mobility aid caps, not the 50 cm | as above | `risk.profile.MobilityAid.cap_m` | Cited: no study measures the stability of an occupied wheelchair or scooter in floodwater, and Smith, Davey & Cox (2014) advise that vulnerable people avoid flowing floodwater under all conditions; the walker thresholds (30 cm vulnerable use, 50 cm H2) are therefore not applied. A downgrade offers only the next level of the same device, never above its cap |
| Steps for wheelchair users | impassable | `risk.access.can_use` | Cited: AS 1428.1 (Design for access and mobility) requires an accessible path of travel without steps; stairways are not part of it. Edges come from OSM `highway=steps` (`is_steps`) |
| Steepest path for mobility aid users | 1:14 (7.1%); steeper is impassable | `risk.access.MAX_GRADIENT`, `network.gradient.STEEPEST_RAMP` | Cited: AS 1428.1 allows ramps up to 1:14 and walkways up to 1:20 (5%); a gradient of exactly 1:14 is allowed. Gradients come from the City of Melbourne's footpath steepness data (see Footpath gradients below); OSM's `incline` gives none in Southbank (of 1,024 tagged ways, all `up`, `down` or `yes`). An edge without a measured gradient counts as passable |
| The same limit for powered wheelchairs and mobility scooters | 1:14 | `risk.access.MAX_GRADIENT` | **Judgement**: powered devices are rated for more (Invacare Storm⁴ manual: dynamic stability 6°, 10.5%, under ISO 7176-2; maximum safe slope 8° to 11.3° depending on the seat lifter), but ratings are for a dry surface and a set seating position, routes are planned for rain and floods, and AS 1428.1 sets the path for every wheeled aid. One limit for all three devices; a separate one for powered devices is the first value to revisit |
| Accepted heights | 0.5–2.5 m | `risk.profile.TravellerProfile` | Chosen: input check |
| Walking speed | 1.3 m/s | `risk.profile.DEFAULT_WALKING_SPEED_M_S` | Chosen: a typical adult pace; only used for travel times |

## Alerts at the start

| Parameter | Value | Where | Basis |
|---|---|---|---|
| Deep | over 50 cm | `risk.alerts` | The hard limit; for most adults the knee comes first, so this level applies only to people taller than about 175 cm |
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
| Access leg passing a flight of steps | within 0.5 m of the flight without its end metres (a quarter of it if shorter), or within 1 m of both its ends | `routing.router.STEPS_CLEARANCE_M`, `STEPS_END_M` | Chosen: about half the width of a narrow stair. A leg may meet a flight at its top or bottom, but one that runs past it is treated as steps, so wheelchair users cannot skip a flight through the snapping reach |
| Footpaths counted as "standing on" | within 1 m of the nearest | `routing.router.STANDING_TOLERANCE_M` | Chosen: at a corner the traveller stands on the shallowest of these |
| Entrance belongs to a building | within 1.5 m of its outline | `places.resolver` | Chosen: OSM entrance nodes sit on or next to the outline |
| Building without mapped entrances | outline points nearest the footpaths within 60 m, at least 15 m apart | `places.resolver` | Chosen |
| Access points per place | at most 8 | `places.resolver.MAX_ACCESS_POINTS` | Chosen: bounds the search |
| Refuge search | 800 m straight line, nearest 25 buildings | `places.refuges` | Chosen: about ten minutes' walk; beyond it, emergency help is offered instead |

## Footpath gradients

City of Melbourne open data, *Footpath steepness*: one gradient per footpath section, the rise
between its lowest and highest surveyed levels over the distance between them
(`sources.steepness`). How an edge takes its gradient is set in `network.gradient`. Measured
figures are for the download area (`config.SOUTHBANK_BBOX`) and the current network.

| Parameter | Value | Where | Basis |
|---|---|---|---|
| Duplicate records | merged into one section per footpath asset and set of values | `sources.steepness` | Measured: the export splits sections into polygon pieces that repeat the same values (7,444 records, 2,122 sections with a gradient) |
| Shortest section used | 5 m run | `network.gradient.MIN_RUN_M` | Cited and chosen: AS 1428.1 allows kerb ramps up to 1:8 over at most 1.52 m and step ramps 1:10 over 1.9 m, so a short section can be steep and still accessible; over a few metres the levels' precision also dominates. Measured: 680 of the 2,122 sections run less than 5 m |
| Section near a bridge | not trusted | `network.gradient.MATCH_M` | Chosen: a footpath polygon at a bridge can take in the deck and the bank below it (e.g. Flinders Walk at Princes Bridge, 58% over 15 m, from 1.4 to 10.3 m AHD). Measured: 30 sections |
| Section joining two levels | steeper than 1:14 and rising more than 2 m: not trusted | `network.gradient.TWO_LEVEL_RISE_M` | Chosen: most are a footpath beside a road climbing onto an overpass (Montague Street at the West Gate Freeway, 96% over 8.5 m, 1.2 to 9.4 m AHD) or the top and bottom of a flight of steps; no accessible ramp rises that much that steeply. Gentle sections that rise more than 2 m over a long run are kept. Measured: 73 sections |
| Edge runs along a section | within 2 m of its polygon | `network.gradient.MATCH_M` | Chosen: OSM lines and the council's polygons are drawn a little apart. Measured: the share of footpath length within reach of a section (5 m or longer) is 46% at 0 m, 52% at 1 m and 55% at 2 m, then grows slowly (57% at 3 m, 59% at 5 m) while a wider reach takes in more neighbouring paths |
| Overlapping sections | the gentlest applies | `network.gradient` | Chosen: a stretch counts as steep only when every section along it agrees, so a section matched by mistake (a parallel path, a corner) cannot make a path impassable |
| Shortest steep stretch | 5 m, sampled every 1 m (the whole edge if shorter) | `network.gradient.MIN_STRETCH_M`, `SAMPLE_SPACING_M` | Chosen: the same length as the shortest section used |
| Bridges and tunnels | no gradient | `network.gradient` | Chosen: the sections beside or under them are at another level |
| Result | 829 of 3,928 edges have a gradient, 23 are steeper than 1:14 (7 of them steps), 1 of those 16 other paths inside Southbank | `scripts/build_network.py` | Measured: 55% of footpath length has a gradient, 68% inside Southbank. Carriageways, private paths and many park paths are not in the data |

## Flood levels

| Parameter | Value | Where | Basis |
|---|---|---|---|
| Level boundaries | ankle, knee, hip | `risk.levels.FloodLevel` | Cited: the waterlines used to grade flood severity from photos of people (Feng, Brenner & Sester, 2020). Knee also matches the 0.5 m H2 limit and children's wading limit (Smith, Davey & Cox, 2014) and Melbourne Water's 500 mm pedestrian access limit |
| Hip height | 0.530 × height | `risk.levels.HIP_FRACTION` | Cited: Drillis & Contini (1966) |
| Reference adult | 1.70 m: ankle 6.6, knee 48.5, hip 90.1 cm | `risk.levels.REFERENCE_HEIGHT_M` | Cited: Australian adult average 1.69 m (men 175.6, women 161.8 cm; ABS Australian Health Survey 2011–12), rounded |
| Typical depth | length-weighted median depth on flooded footpaths in Southbank | `risk.levels.typical_depth_m` | Chosen: what most of the water on the paths is like, not set by its few deepest spots. Unknown depths are left out |

## Flood scenarios

| Parameter | Value | Where | Basis |
|---|---|---|---|
| Ground model | 5 m cells, metres AHD | `sources.terrain` | Cited: Geoscience Australia 5 m LiDAR DEM (2025) |
| Flood mechanisms | river and storm tide; drain backflow; stormwater ponding | `hazard.terrain` | Cited: Melbourne Water, Southbank Precinct Local Floodplain Development Plan (2026); City of Melbourne Municipal Emergency Management Plan, Flood and Storm Sub-plan (2025) |
| Light: highest normal tide | 0.59 m AHD | `data/scenarios/1-light-flooding.json` | Cited: highest astronomical tide at Williamstown, Port Phillip Bay Coastal Hazard Assessment (Water Technology for DEECA, 2023), Table 2-1 |
| Moderate: 1-in-20-year storm tide | 1.25 m AHD | `data/scenarios/2-moderate-flooding.json` | Cited: GHD for Melbourne Water (2017), Fishermans Bend: Baseline drainage plan options, Table 1 |
| Heavy: 1-in-100-year storm tide today | 1.60 m AHD | `data/scenarios/3-heavy-flooding.json` | Cited: GHD (2017) Table 1; also the major flood level at the VICSES Southbank gauge |
| Extreme: 1-in-100-year storm tide in 2100 | 2.40 m AHD | `data/scenarios/4-extreme-flooding.json` | Cited: GHD (2017) Table 1; 0.8 m of sea level rise, Victoria Planning Provisions clause 13.01-2S |
| Drain inlets | grated, side-entry, lane, trench and headwall pits | `sources.drainage` | Cited: City of Melbourne open data, Stormwater Pits; junctions, nodes and submerged pits are left out because they do not open to the surface |
| Stormwater ponding fill | a quarter (light), full (moderate and above) | `data/scenarios/*.json` | Chosen: no published depth for local ponding in Southbank. A quarter keeps light flooding at ankle depth (6 cm typical; a half fill gives about 10 cm); full is the most a depression holds before it overflows |
| River and dock surface | ground at or below 0.05 m AHD | `hazard.terrain.WATER_SURFACE_M` | Measured: the ground model flattens river and dock surfaces to 0 m AHD (17,324 of the 20,150 cells at or below this level are exactly 0) |
| Unreliable ground | land the 0.59 m tide reaches overland | `hazard.terrain.HIGHEST_TIDE_M` | Derived: such land would flood at ordinary high tides, which Southbank's paths do not (VICSES: the promenade starts to flood at 1.1 m). These cells are excavations and filled voids in the ground model; their depth is left unknown |
| Pits lifted | more than 0.5 m below the median of a 25 m window | `hazard.terrain` | Chosen: removes basement ramps and cuttings, which would otherwise read as metres of water beside a footpath |
| Ground smoothing | 3 × 3 cell median | `hazard.terrain.GROUND_FILTER_CELLS` | Chosen: removes single-cell noise |
| Sampling along an edge | every 2 m | `hazard.grid.SAMPLE_SPACING_M` | Chosen: finer than the 5 m cells, so no cell an edge crosses is skipped |

## Languages

The web client is offered in English and the four languages below (see [languages.md](languages.md)
for how they are translated). Source: Australian Bureau of Statistics, 2021 Census of Population
and Housing, QuickStats, "Language used at home", for
[Southbank](https://abs.gov.au/census/find-census-data/quickstats/2021/SAL22315) (suburb, SAL22315,
22,631 people) and
[Southbank (West) – South Wharf](https://abs.gov.au/census/find-census-data/quickstats/2021/206041508)
(SA2 206041508, 6,463 people).

| Language used at home | Southbank (suburb) | Southbank (West) – South Wharf | Offered as | Basis |
|---|---|---|---|---|
| English only | 45.4% | 46.2% | English | Cited |
| Mandarin | 11.6% | 11.3% | Chinese (Simplified) | Cited |
| Spanish | 5.3% | 3.5% | Spanish | Cited |
| Hindi | 4.0% | 3.4% | Hindi | Cited |
| Cantonese | 3.1% | 2.9% | Chinese (Simplified) | Cited; **Chosen**: Mandarin and Cantonese are both written in Chinese characters, so one written form covers them, and Simplified is offered. Cantonese speakers who read Traditional characters are not specifically served |
| Indonesian | 2.1% | not in the top five | not offered | **Chosen**: fifth across the whole suburb, and not offered; the project chose Korean instead |
| Korean | not in the top five | 2.0% | Korean | Cited: the fifth language in the western part of Southbank. **Chosen**: offered in place of Indonesian |
