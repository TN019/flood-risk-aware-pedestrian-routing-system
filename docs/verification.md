# Verification: predictions

This document states, **before running the program**, what the routing rules should produce in a
set of test cases (A–I). The predictions are derived by hand from the rules in
[architecture.md](architecture.md). `backend/scripts/verify.py` then runs the same cases and
compares its results with these predictions; see `reports/verification_results.md`.

Verification asks whether the program follows its rules. It does not show that the rules are the
right ones for real pedestrians (validation), and the flood conditions are static estimates, not
hydraulic model results.

## Rules used in the derivations

- A traveller's depth limit = body-part fraction × height, capped at 50 cm; no wading = 2 cm.
  Fractions: ankle 0.039, lower calf 0.121, mid calf 0.162, knee 0.285.
- A traveller with a mobility aid picks a level of their device instead: manual wheelchair 2 cm
  (no water), 5 cm (below a 4-inch castor axle), 7.5 cm (below a 6-inch castor axle); powered
  wheelchair 2 cm or 5 cm (well below the chassis); mobility scooter 2 cm or 2.5 cm (a shallow
  puddle). The highest level of each device is its cap.
- Water deeper than the limit (or of unknown depth) is impassable. Up to 2 cm counts as dry.
- Risk R = depth ÷ limit. Edge cost = length × (1 + α·R) for a fully flooded edge, α = 2 unless
  stated. The recommended route minimises total cost.
- Alert levels at the start: over 50 cm = DEEP; above the knee (0.285 × height) = VERY_DEEP; above
  half the height = CRITICAL.
- Emergency help: at the start's alert level (DEEP: available; VERY_DEEP: recommended; CRITICAL:
  strongly recommended); as the only option when the start is outside, no route fits the limit and
  no refuge can be reached; and, for a start inside a building (no alert level), as **available**
  when the traveller is cut off: no route fits the limit and no downgrade is offered (the least
  water is beyond the hard limit or the device's cap, or of unknown depth).
- A downgrade is offered only when the start is at most OVER_LIMIT, and only up to 50 cm; for a
  mobility aid, it is the lowest higher level of the same device that covers the least water,
  never above that device's cap.
- Walking speed 1.3 m/s.
- Mobility aid users (any of the three devices; "wheelchair" below) never use steps: an edge marked
  as steps is impassable for them in every search
  (shortest ignoring flooding, shortest within limit, recommended, least water, refuge). For
  everyone else steps are ordinary paths.

Limits used below:

| Traveller | Height | No wading | Ankle | Lower calf | Mid calf | Knee | Half height |
|---|---|---|---|---|---|---|---|
| Adult | 1.70 m | 2.00 cm | 6.63 cm | 20.57 cm | 27.54 cm | 48.45 cm | 85 cm |
| Child | 1.20 m | 2.00 cm | 4.68 cm | 14.52 cm | 19.44 cm | 34.20 cm | 60 cm |
| Tall adult | 1.90 m | 2.00 cm | 7.41 cm | 22.99 cm | 30.78 cm | 54.15 cm (limit 50 cm) | 95 cm |

## Part 1 — exact predictions on a test town

A small network where every number can be worked out by hand:

```
T0 ──t01── T1 ──t12── T2 ──t23── T3        y = 50 m
│          │          │          │
c0         c1         c2         c3        connectors, 50 m each
│          │          │          │
B0 ──b01── B1 ──b12── B2 ──b23── B3        y = 0 m;  B0 = (0, 0), B3 = (300, 0)
```

Street segments are 100 m; connectors 50 m. Trips go from B0 to B3 unless stated. The shortest
way is the bottom street, 300 m. Every way that avoids b12 uses one detour of
50 + 100 + 50 m in place of b12's 100 m, so it is **400 m** (several 400 m paths exist; only the
length is predicted). Building "Shelter" occupies x −40…−10, y 10…40, with a door on its east
wall at (−10, 25), 10 m from connector c0.

Water covers whole edges at the stated depth.

### A — normal conditions

No water. Adult, ankle limit.

| Prediction | Value |
|---|---|
| Shortest, shortest within limit, recommended | all 300 m, the same route |
| Travel time | 300 / 1.3 = 230.8 s |
| Deepest water, edges over the limit | none, 0 |
| Downgrade, refuge, emergency | none |

### B — unsafe edge is excluded

b12 at 10 cm. Adult, ankle limit (6.63 cm): b12 is impassable.

| Prediction | Value |
|---|---|
| Shortest ignoring flooding | 300 m through b12; deepest 10 cm, "up to the lower calf"; 100 m in water; 1 section over the limit |
| Shortest within limit | 400 m, dry |
| Recommended, for α = 0, 2 and 10 | 400 m, dry (an impassable edge is never used, whatever α) |
| Network edges over the limit | 1 |

### C — lower-risk detour

Adult, mid-calf limit (27.54 cm), α = 2 unless stated.

| Case | Derivation | Recommended |
|---|---|---|
| C1: b12 at 20 cm | R = 0.20 / 0.2754 = 0.7262; b12 costs 100 × (1 + 2 × 0.7262) = 245.2, so the bottom street costs 445.2 > 400 | **400 m**, dry; shortest within limit is 300 m with 100 m in 20 cm |
| C2: b12 at 10 cm | R = 0.3631; b12 costs 172.6; bottom 372.6 < 400 | **300 m**, 100 m in 10 cm |
| C3: b12 at 20 cm, α = 1.3 | b12 costs 100 × (1 + 1.3 × 0.7262) = 194.4; bottom 394.4 < 400 | **300 m** |
| C4: b12 at 20 cm, α = 1.5 | b12 costs 208.9; bottom 408.9 > 400 | **400 m** |

The switch happens at α = 1 / 0.7262 = 1.377.

### D — different travellers, same flood

b12 at 10 cm, α = 2. Bottom street costs 200 + 100 × (1 + 2R); the detour costs 400.

| Traveller | Limit | R | Bottom cost | Recommended |
|---|---|---|---|---|
| Adult, mid calf | 27.54 cm | 0.3631 | 372.6 | **300 m** |
| Adult, lower calf | 20.57 cm | 0.4861 | 397.2 | **300 m** (2.8 m margin) |
| Adult, ankle | 6.63 cm | — | impassable | **400 m** |
| Child, mid calf | 19.44 cm | 0.5144 | 402.9 | **400 m** (2.9 m margin) |
| Child, lower calf | 14.52 cm | 0.6887 | 437.7 | **400 m** |
| Wheelchair | 2 cm | — | impassable | **400 m** |

### E — no route within the limit

| Case | Setup | Predictions |
|---|---|---|
| E1 | b12 and t12 at 40 cm (every way crosses one). Adult, mid calf. Start B0 (dry) | No route within limit. Shortest ignoring flooding 300 m, deepest 40 cm, "up to the knee". **Downgrade to the knee** (48.45 cm ≥ the 40 cm every way needs; ≤ 50 cm): 300 m via b12. **Refuge "Shelter", 35 m** (25 m up c0 + 10 m to the door), dry, within the limit. Start level OK, no emergency |
| E2 | b12 at 15 cm, t12 at 25 cm. Adult, ankle | No route within limit. **Downgrade to lower calf** (20.57 cm): the least water to face is **15 cm** (via b12), route **300 m**. Refuge "Shelter", 35 m, within limit. No emergency |
| E3 | b12 and t12 at 40 cm. Adult, mid calf. Start (150, 0), standing in b12 | Start depth 40 cm → **OVER_LIMIT** (> limit 27.54 cm, ≤ knee 48.45 cm, ≤ 50 cm). **No emergency** (a refuge exists). **Downgrade to the knee**: least water 40 cm, 50 m east in b12 + 100 m = **150 m**. Refuge "Shelter" by the safest way: 50 m west in b12 + 100 m + 25 m + 10 m = **185 m**, deepest 40 cm, **not within the limit** |
| E4 | As E3, water 90 cm | 90 cm > 85 cm half height → **CRITICAL**, emergency **"strongly recommended"** |
| E5 | As E3, child, mid calf | 40 cm > child knee 34.2 cm → **VERY_DEEP**, emergency **"recommended"** |
| E6 | As E1 but no buildings | No route, no refuge → emergency **"only option"** |
| E7 | b12 and t12 at 60 cm. Adult, mid calf. Start B0 (dry) | No route within limit. **No downgrade** (60 cm > 50 cm). Refuge "Shelter", 35 m, within the limit. Start level OK, no emergency |
| E8 | b12 and t12 at 52 cm. Tall adult (1.90 m), mid calf. Start (150, 0), standing in b12 | 52 cm > 50 cm, ≤ knee 54.15 cm → **DEEP**, emergency **"available"**, SOS depth 52 cm. **No downgrade** (start deeper than OVER_LIMIT). Refuge "Shelter" by the safest way, **185 m**, deepest 52 cm, **not within the limit** |

### F — switching conditions

Same router, same trip and traveller (adult, ankle), conditions switched normal → B's flood →
normal: recommended **300 → 400 → 300 m**; edges over the limit **0 → 1 → 0**. Nothing from one
run carries into the next.

### G — steps and wheelchair users

The same town with some edges marked as steps (no other change). Adult, ankle limit (6.63 cm)
against a wheelchair user (2 cm, no steps). Start B0 unless stated.

| Case | Setup | Predictions |
|---|---|---|
| G1 | b12 is steps. No water | Adult: shortest, shortest within limit and recommended all **300 m**, through b12 (steps are ordinary paths for walkers); no steps reported as avoided. Wheelchair: all three **400 m**, none through b12; steps reported as avoided. Edges over the limit for the wheelchair user: **0** (steps are not water) |
| G2 | b12 is steps, t12 at 10 cm | Adult: t12 is over the limit, b12 is usable: recommended **300 m**. Wheelchair: every way from x = 100 to x = 200 uses b12 (steps) or t12 (10 cm > 2 cm), so **no route within the limit**. Shortest ignoring flooding **400 m** (step-free, through t12). Least water **10 cm**, route **400 m** (the dry 300 m way has steps). No downgrade. Refuge "Shelter", **35 m**, within the limit. Start level OK, no emergency |
| G3 | c0 is steps, b12 and t12 at 10 cm | Adult: no route within limit; downgrade to the lower calf, least water 10 cm, route 300 m; refuge "Shelter", **35 m** up c0, within the limit; no emergency. Wheelchair: no route within limit; least water **10 cm**, route **300 m** (via b12, no steps); no downgrade; the Shelter door joins the network only on c0 (the bottom and top streets are 26.9 m from it, beyond the 10 + 15 m snapping reach), so **no refuge** is offered; emergency **"only option"** |

### H — mobility aids and their levels

The town without steps. Start B0, α = 2. Limits: manual wheelchair 2 / 5 / 7.5 cm, powered
wheelchair 2 / 5 cm, mobility scooter 2 / 2.5 cm.

| Case | Setup | Predictions |
|---|---|---|
| H1 | b12 at 4 cm. Manual wheelchair, no water (2 cm) | b12 is impassable: shortest within limit and recommended **400 m**, dry |
| H2 | As H1, manual wheelchair at 5 cm | R = 0.04 / 0.05 = 0.8; b12 costs 100 × (1 + 2 × 0.8) = 260, so the bottom street costs 460 > 400: recommended **400 m**. Shortest within limit (α = 0) **300 m** through b12, deepest 4 cm |
| H3 | As H1, mobility scooter at 2.5 cm | 4 cm > 2.5 cm: b12 is impassable; recommended **400 m** |
| H4 | b12 and t12 at 4 cm. Manual wheelchair, no water | No route within the limit. Least water **4 cm**, route **300 m**. Downgrade to **"below a 4-inch castor axle"** (5 cm ≥ 4 cm), route **300 m**. Refuge "Shelter", **35 m**, within the limit. No emergency |
| H5 | As H4, mobility scooter, no water | No route within the limit. Least water 4 cm. **No downgrade** (4 cm > the scooter's 2.5 cm cap). Refuge "Shelter", 35 m, within the limit |
| H6 | b12 and t12 at 7 cm. Powered wheelchair, no water; manual wheelchair, no water | Powered: **no downgrade** (7 cm > its 5 cm cap). Manual: downgrade to **"below a 6-inch castor axle"** (7.5 cm ≥ 7 cm; 5 cm is not enough), route **300 m** |

### I — cut off inside a building

The town without steps, α = 2. Start inside "Shelter" (any point in it): the start is sheltered,
with no alert level, and no refuge is searched for. Its one door is 10 m from c0 at (0, 25), so
the shortest way to B3 is 10 + 25 (down c0) + 300 (bottom street) = **335 m**; the way over the
top street is 10 + 25 + 300 + 50 = 385 m. Every way from x = 100 to x = 200 uses b12 or t12.

| Case | Setup | Predictions |
|---|---|---|
| I1 | No water. Adult, ankle | Sheltered. Recommended **335 m**. No emergency |
| I2 | b12 and t12 at 60 cm. Adult, mid calf (27.5 cm) | No route within the limit. Least water **60 cm**, route **335 m** (tie on depth, shortest). **No downgrade** (60 cm > 50 cm). No refuge (already inside). Emergency help **available**, reason **cut off** |
| I3 | b12 and t12 at 40 cm. Adult, mid calf | Least water 40 cm. Downgrade to the **knee** (48.45 cm ≥ 40 cm), route **335 m**. **No emergency**: a way out within 50 cm exists |
| I4 | b12 and t12 of unknown depth. Adult, ankle | Least water of **unknown depth**. No downgrade. Emergency help **available**, reason **cut off** |
| I5 | As I2, but starting outside at B0 (dry) | Not sheltered, start level OK. No downgrade. Refuge "Shelter", **35 m**, within the limit. **No emergency** (the rule is for a start inside only) |
| I6 | b12 and t12 at 10 cm. Manual wheelchair, no water, inside Shelter | Least water 10 cm, route 335 m. No downgrade (10 cm > the 7.5 cm cap). Emergency help **available**, reason **cut off** |

## Part 2 — properties on the Southbank network

On the real network exact routes cannot be worked out by hand, so the predictions are properties
that must hold for every trip. 100 random trips inside Southbank (fixed seed), the five bundled
flood levels.

| # | Prediction |
|---|---|
| R-A | Normal conditions: for every trip and traveller, the recommended route equals the shortest route |
| R-B | Every level, every traveller: no recommended route or shortest-within-limit route uses water deeper than the traveller's limit |
| R-C | Whenever both exist, the recommended route's risk cost is ≤ the risk cost of the shortest-within-limit route, and ≤ that of the flood-ignoring shortest route if that one is passable |
| R-D | Same height: a trip possible with a stricter limit is possible with every looser one (no wading ⇒ ankle ⇒ lower calf ⇒ mid calf ⇒ knee) |
| R-E | Every trip without a route within the limit offers at least one way forward: a downgrade, a refuge, being sheltered, or emergency help |
| R-F | For a fixed traveller (adult, ankle), the number of network edges over the limit rises strictly from normal to extreme, and the share of trips with a route within the limit never rises |
| R-G | Every level, every trip: no route planned for a mobility aid user (shortest ignoring flooding, shortest within limit, recommended, least water, refuge) uses steps |
| R-H | Same device: a trip possible for a manual wheelchair at a lower level is possible at every higher one (no water ⇒ 5 cm ⇒ 7.5 cm) |

## Results

Run with `uv run python backend/scripts/verify.py` (100 trips per level on the Southbank network);
the full table is written to `reports/verification_results.md`.

**First run: 66 of 67 checks met.** All 44 exact predictions on the test town matched, including
the two narrow cases in D (2.8 m and 2.9 m margins) and the α switch-over between C3 and C4. On the
Southbank network R-A to R-E held at every level, for 100 trips × 6 travellers each.

**Mismatch, R-F: the prediction was wrong, not the program.** It said the number of network edges
over the *ankle* limit (6.6 cm) rises strictly from level to level. The run gave
(0, 0, 95, 912, 2,272): light ponding is 3–5 cm by design (its description says it only blocks
people who will not wade at all), so for an ankle limit it adds no impassable edges, the same as
normal conditions. The prediction contradicted the scenario's own definition.

**Revised R-F**, written after the first run and labelled "(revised)" in the report:

- edges over the ankle limit never fall from one level to the next;
- edges over the no-wading limit (2 cm) rise strictly from level to level.

Second run: **68 of 68 checks met**. Edges over the no-wading limit by level:
(0, 62, 129, 965, 2,272); trips possible at the ankle limit: (100, 100, 90, 30, 14) of 100.

**Third run, after the scenarios were rebuilt from published flood levels and terrain** (see
architecture.md): the predictions were not changed, and **68 of 68 checks met**. Edges over the
no-wading limit by level: (0, 145, 1,191, 1,539, 2,252); trips possible at the ankle limit:
(100, 98, 23, 12, 2) of 100.

**Fourth run, after stormwater ponding was extended from the official overland-flow extents to
every terrain depression** (light ponding a quarter full, levels 2–4 full): predictions unchanged,
**68 of 68 checks met**. Edges over the no-wading limit by level: (0, 152, 1,526, 1,781, 2,341);
trips possible at the ankle limit: (100, 97, 17, 10, 2) of 100.

**Fifth run, after the levels were redefined by depth on the body and drain backflow was added**
(light, moderate, heavy and extreme flooding; see architecture.md): predictions unchanged, **68 of
68 checks met**. Edges over the no-wading limit by level: (0, 169, 1,165, 1,526, 2,341); trips
possible at the ankle limit: (100, 93, 20, 17, 2) of 100.

**Sixth run, after the hard limit was raised from 30 cm to 50 cm and the knee added as a limit.**
Before running, E1 and E3 were re-derived under the new rules (above: E1 now offers a downgrade
to the knee; in E3 40 cm is OVER_LIMIT, so there is a downgrade and no emergency), and E7 and E8
were added to keep testing what E1 and E3 used to test: water beyond the hard limit (no
downgrade) and the DEEP level (only reachable by people taller than about 175 cm). Part 2 adds a
knee traveller to R-A to R-E. Result: **76 of 76 checks met**.

**Seventh run, after wheelchair users were kept off steps.** Case G (test town) and R-G
(Southbank) were derived and committed before the change. To keep R-A from failing on a trip with
no step-free route, it now counts only trips whose recommended route was found; the prediction
is unchanged. Result: **101 of 101 checks met**, including all 20 in G. Without the step rule, 8
of the G checks fail. On the Southbank network only 1 of the 100 random trips has steps on its
plain shortest way, so R-G tests little there; case G and the unit tests carry most of the weight.

An extra check outside these predictions, 160 trips through `/api/trip` between the two ends of
randomly chosen flights of steps (both directions, normal and moderate flooding), then found a gap
that R-G could not see: for 64 of the 72 trips whose
walking route used the steps, the wheelchair route was just as short. Its straight access leg ran
from the bottom of a short flight to the footpath at its top, within the 15 m snapping reach, so
no network edge on the route was steps. Access legs that run past a flight are now treated as
steps (architecture.md, "Mobility aid users"), with two unit tests that fail without the rule. After
that, 92 walking routes count as using steps (legs included) and none of the wheelchair routes
uses steps or is as short as the walking route.

**Eighth run, after wheelchair users got device levels.** Case H (test town), R-H and the wider
R-G (Southbank) were derived and committed before the change; the Southbank trips now also run for
a manual wheelchair at 5 cm and 7.5 cm and a mobility scooter at 2.5 cm. Result: **121 of 121
checks met**, including all 15 in H. The one random trip whose plain shortest way has steps is
now counted once for each of the four mobility aid travellers (4), and none of their routes uses
steps. No manual wheelchair trip is possible at a lower level but not a higher one.

**Ninth run, after travellers cut off inside a building got emergency help.** Case I (test town)
was derived and committed before the change; against the code before it, 14 of its 17 checks
already held, and the three emergency checks (I2, I4, I6) failed, as predicted. Result: **138 of
138 checks met**, including all 17 in I. Calling for help (000, VICSES 132 500, an alert to
people nearby) is now always available in both clients; these rules decide only when the results
put it first.
