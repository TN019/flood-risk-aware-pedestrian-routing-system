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
program: only an inspection on site can, and section 3.2 gives the method.

## 1. Correctness of the algorithms

### 1.1 Path finder against a reference

The in-house Dijkstra against NetworkX's, under the walking cost: 1,000 random node pairs searched
directly, and 300 random trips through the router (snapping, access legs).

**Prediction:** every node pair has the same cost (or no path for both), and every trip the same
length.

### 1.2 Safest-path search against brute force

The two-phase minimax search (lowest possible deepest point, then the cheapest path that never goes
deeper) against enumerating every simple path, on 300 random graphs of 9 nodes and 16 edges with
random lengths and depths, 3 node pairs each.

**Prediction:** for every connected pair, the same deepest point and the same length.

### 1.3 Hand-derived predictions

The test town cases A–I and the Southbank properties R-A to R-H in
[verification.md](verification.md).

**Prediction:** every check is met.

### 1.4 Fault injection

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

**Prediction:** every fault makes at least one test fail.

## 2. Continuous pedestrian safety

### 2.1 Safety and what it costs

100 random trips (fixed seed) at each flood level, for four travellers: an adult with an ankle
limit, an adult with a mid-calf limit, a child with a mid-calf limit, and a manual wheelchair at
5 cm. For each: the share of trips with a route within the limit; for trips whose plain shortest
way crosses water over the limit, how much longer the recommended route is and how much water over
the limit it avoids; and for trips with no route, what is offered instead.

**Prediction:** no recommended route crosses water over the traveller's limit. The rest is a
measurement.

### 2.2 Rising flood: rerouting on the way

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

## 3. Public area accessibility

### 3.1 Step-free connectivity

300 random pairs of buildings inside Southbank, normal conditions: the walking route and the
step-free route a manual wheelchair user gets.

**Predictions:** no step-free route uses steps, and none is shorter than the walking route between
the same buildings (a step-free route is also a walking route). The share of pairs with a step-free
route and how much longer it is are measurements.

### 3.2 Field inspection (ground truthing)

The network and entrances come from OpenStreetMap, which can miss steps, kerbs, barriers and
closures, or mark an entrance that is not open to the public. Only an inspection on site can tell.

1. `uv run python scripts/ground_truth_sample.py` draws a sample, stratified by kind: footpaths,
   crossings, steps and paths beside a carriageway, and building entrances used as shelters. It
   writes a checklist (CSV) with what the model says about each item and empty columns for the
   inspector.
2. On site, for each item: is it passable, are there steps, is there a kerb ramp, how steep is it,
   how wide, the surface, any barrier or closure, is the entrance step-free and open to the public;
   with a photo reference.
3. `uv run python scripts/ground_truth_compare.py <filled.csv>` compares the inspection with the
   model: agreement on each attribute, and above all the **false accessible rate**, the share of
   items the model treats as usable (or step-free) that are not. That is the error that could send
   someone where they cannot go.

No prediction: the results appear on `/benchmark` once an inspection has been filed as
`data/ground_truth/inspected.csv`.

## 4. Performance

Time to plan a whole trip (routes, least water, downgrade, refuge, emergency) on the Southbank
network, from the trips in 2.1: median and 95th percentile by flood level. A measurement.

## Results

Written after each run; the full figures are in `docs/benchmark.json` and on `/benchmark`.
