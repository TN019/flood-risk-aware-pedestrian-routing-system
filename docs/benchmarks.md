# Benchmarks

What the routing engine can show about its own correctness, the safety it gives and what that
costs, and the accessibility of what it routes over. `backend/scripts/benchmark.py` runs every
benchmark below on the Southbank network and writes the results to `docs/benchmark.json`, which the
web app shows at `/benchmark` (reached only by its address).

As in [verification.md](verification.md), the predictions here were written **before the first
run**. Some benchmarks are measurements with no prediction; they say so.

Two layers are tested differently. Whether the **algorithms** follow their rules on given data can
be checked automatically, on made-up data (the test town) and on the real network. Whether the
**data** matches the streets (steps, kerbs, gradients, barriers, entrances) cannot be checked by the
program: only an inspection on site can, and section 4 gives the method.

## Algorithm layer

Whether routes follow their rules on the data they are given: on the test town and on the Southbank
network, automatically.

### Correctness

#### 1.1 Path finder against a reference

The in-house Dijkstra against NetworkX's, under the walking cost: 1,000 random node pairs searched
directly, and 300 random trips through the router (snapping, access legs).

**Prediction:** every node pair has the same cost (or no path for both), and every trip the same
length.

#### 1.2 Safest-path search against brute force

The two-phase minimax search (lowest possible deepest point, then the cheapest path that never goes
deeper) against enumerating every simple path, on 300 random graphs of 9 nodes and 16 edges with
random lengths and depths, 3 node pairs each.

**Prediction:** for every connected pair, the same deepest point and the same length.

#### 1.3 Hand-derived predictions

The test town cases A–J and the Southbank properties R-A to R-I in
[verification.md](verification.md).

**Prediction:** every check is met.

#### 1.4 Fault injection

Each fault below breaks one safety rule on purpose; the whole test suite (unit tests and the test
town cases) then runs against the broken code. A test suite that misses a fault would not notice
that rule breaking in a real change.

| Fault | What it breaks | Predicted to fail, at least |
|---|---|---|
| F1 | Water deeper than the limit is passable | B, E (test town); unit tests of the risk model |
| F2 | Water of unknown depth counts as dry | I4; unit tests of the risk model |
| F3 | No 50 cm hard limit for walkers | the unit test capping a 2 m traveller's knee at 50 cm. The test town does **not** catch it: the cap binds only for people taller than about 175 cm |
| F4 | Wheelchair users may use steps | G; unit tests of the step rule |
| F5 | No refuge is offered | E, G, H, I5 |
| F6 | No downgrade is offered | E, H4, H6, I3 |
| F7 | No emergency help when cut off inside a building | I2, I4, I6 |
| F8 | No emergency help at all | E4, E5, E6, E8, G3, I2 |
| F9 | The recommended route ignores water within the limit (α = 0) | C, D, H2 |
| F10 | Mobility aid users may use paths steeper than 1:14 | J; unit tests of the gradient rule. G does **not** catch it: steps are a separate rule |

**Prediction:** every fault makes at least one test fail.

### Pedestrian safety

#### 2.1 Safety and what it costs

100 random trips (fixed seed) at each flood level, for four travellers: an adult with an ankle
limit, an adult with a mid-calf limit, a child with a mid-calf limit, and a manual wheelchair at
5 cm. For each: the share of trips with a route within the limit; for trips whose plain shortest
way crosses water over the limit, how much longer the recommended route is and how much water over
the limit it avoids; and for trips with no route, what is offered instead.

**Prediction:** no recommended route crosses water over the traveller's limit. The rest is a
measurement.

#### 2.2 Rising flood: rerouting on the way

100 random trips for an adult with a mid-calf limit, walking at 1.3 m/s while the flood rises:
light flooding at the start, moderate after 4 minutes, heavy after 8. At every rise the trip is
planned again from where the traveller is, and they follow the new advice: the recommended route,
the way to a shelter, or staying where they are.

**Predictions:**

- No metre is walked in water deeper than the limit on a route that was given as within the limit
  (each part of a route is walked under the flood level it was planned for).
- Every trip ends with advice: arrived, at a shelter, staying inside, a higher limit offered, or
  emergency help offered. None ends with nothing to do.

The number of reroutes, the outcomes and the extra distance are measurements.

### Public area accessibility

#### 3.1 Step-free connectivity

300 random pairs of buildings inside Southbank, normal conditions: the walking route and the
step-free route a manual wheelchair user gets.

**Predictions:** no step-free route uses steps, and none is shorter than the walking route between
the same buildings (a step-free route is also a walking route). The share of pairs with a step-free
route and how much longer it is are measurements.

**Revised after the first run:** no step-free route **costs** less than the walking route. The first
prediction confused length with cost: routes minimise walking cost, with a carriageway counted three
times its length, so a step-free route may be shorter while costing more (see Results).

**Added with footpath gradients** (written before the run with gradients): the route a manual
wheelchair user gets also leaves out paths steeper than 1:14, so no step-free route uses one, none
costs less than the walking route, and the share of pairs with a step-free route is no higher than
before (a rule that only removes edges cannot connect more pairs).

## Data layer

### 4. Field inspection (ground truthing)

The network and entrances come from OpenStreetMap, which can miss steps, kerbs, barriers and
closures, or mark an entrance that is not open to the public. Only an inspection on site can tell.

1. `uv run python scripts/ground_truth_sample.py` draws a sample, stratified by kind: footpaths,
   crossings, steps, paths steeper than 1:14 and paths beside a carriageway, and building entrances
   used as shelters. Steep paths are rare inside Southbank (one in the current network), so that
   kind is also drawn from the network's margin, which routes use to cross the river, after every
   steep path inside Southbank. It writes a
   checklist (CSV) with what the model says about each item, its measured gradient among them, and
   empty columns for the inspector.
2. On site, for each item: is it passable, are there steps, is there a kerb ramp, how steep is it,
   how wide, the surface, any barrier or closure, is the entrance step-free and open to the public;
   with a photo reference. The gradient is recorded as flat, gentle or steep (steeper than 1:14,
   about 4°; a phone's level app is enough).
3. `uv run python scripts/ground_truth_compare.py <filled.csv>` compares the inspection with the
   model: agreement on each attribute, and above all the **false accessible rate**, the share of
   items the model treats as usable (or step-free) that are not. That is the error that could send
   someone where they cannot go. For gradients it is the share of paths treated as no steeper than
   1:14 (or not measured) that are steep on site; the share of paths treated as steep that are not
   shows the detours wheelchair users are sent on for nothing.

No prediction: once an inspection has been filed as `data/ground_truth/inspected.csv`, the next
run writes the comparison to `docs/benchmark.json` (`field`); `/benchmark` shows only the algorithm
layer.

## Results

Written after each run; the full figures are in `docs/benchmark.json` and on `/benchmark`.

**First runs.** The first attempt stopped with an error in 2.2 (below); after that fix the run
completed; clean reruns on commits `4add2c3` and `1fac09a` gave the same figures.

- **1.1** Same cost for **1,000 of 1,000** node pairs and same length for **300 of 300** trips. As
  predicted.
- **1.2** **891 of 891** connected pairs agree with brute force. As predicted.
- **1.3** Test town **104 of 104**, Southbank properties **34 of 34**. As predicted.
- **1.4** Every fault is caught. Tests failed, of 241: F1 27, F2 3, F3 6, F4 12, F5 8, F6 8, F7 4,
  F8 9, F9 2. The test town cases that fail are those predicted, and F3 is caught by unit tests
  only, not by the test town, as predicted. As written, the suite has no failures.
- **2.1** No recommended route crosses water over the limit in **1,600** plans. As predicted.
  Measured, for example: under light flooding an adult with an ankle limit has a route for 86 of 100
  trips; for the 36 whose shortest way crosses water over the limit, the recommended route is 0.8%
  longer at the median and avoids 66 m of it. Under extreme flooding 2–3 of 100 trips have a route,
  and a shelter is offered for 96–98 of the rest.
- **2.2** **0 m** walked over the limit on routes given as within it, and every trip ends with
  advice (arrived 31, at a shelter 67, a higher limit offered 2). As predicted. 141 reroutes in 97
  trips; 21 times the water had risen over the limit where the traveller stood, and the safest ways
  out crossed 679 m of it in all.
  **Not foreseen:** the first attempt stopped because 6 times the flood rose while a route ran
  through the network's margin outside Southbank, where no trip can be planned (a start must lie
  inside). The simulation now keeps the traveller on the route they have and counts it: they walked
  **1,435 m** over the limit there in all. This is a gap in the app as well: replanning should work
  wherever a route can go.
- **3.1** No step-free route uses steps. **Not as predicted:** 1 of 299 step-free routes is shorter
  than the walking route (1,887 m against 1,905 m). The prediction was wrong, not the router: routes
  minimise walking cost, with a carriageway counted three times its length, and that step-free route
  costs more (1,968 against 1,944) while being shorter. Revised prediction, by cost: **0 of 299**
  cost less. Measured: a step-free route exists for 299 of 300 pairs and is the walking route itself
  for 279; it is 39.8% longer at most.
- **4** No inspection filed yet.

**Run with footpath gradients** (commit `4453b9b`, after mobility aid users were kept off paths
steeper than 1:14; the predictions for F10 and 3.1 were written before it).

- **1.1, 1.2** Unchanged: 1,000 of 1,000 node pairs, 300 of 300 trips, 891 of 891 pairs agree.
- **1.3** Test town **130 of 130** (26 new checks in J), Southbank properties **39 of 39** (R-I at
  every level). As predicted.
- **1.4** Every fault is caught; as written the suite has no failures (253 tests). **F10** fails 6
  tests and the test town cases J1–J4 only, not G, as predicted. F4 now also fails J, since it
  lets mobility aid users use every edge; F1, F5, F6 and F8 also fail parts of J3 and J4, which
  include water, refuges and emergency help.
- **2.1, 2.2** The same figures as before: no random trip inside Southbank meets one of the 16 steep
  paths that are not steps, as only one of them lies inside Southbank.
- **3.1** No step-free route uses steps or a path steeper than 1:14 (**0** and **0**), none costs
  less than the walking route, and a step-free route exists for **299 of 300** pairs, as before, so
  not more. As predicted. None of the 300 walking routes uses a steep path either, so this
  benchmark does not exercise the rule; case J, R-I and the unit tests carry it. The one pair
  without a step-free route (pair 198 with seed 2026) is from A Block, 256–310 St Kilda Road,
  whose only mapped entrance is reached by a flight of steps (OSM way 222721539); the other
  building reaches the network step-free.
- **4** No inspection filed yet. The sample now has a steep kind: 15 of the 16 steep paths that are
  not steps, the one inside Southbank first and 14 in the margin.

