# Flood Risk-Aware Pedestrian Routing

Walking routes for Southbank, Melbourne that minimise exposure to flood hazards instead of only
distance. The routing engine works on a real pedestrian network; flood conditions come from
interchangeable sources (scenarios built from published flood levels and terrain today, sensors and forecasts later). Each traveller
sets the deepest water they accept as a body part, converted to a depth from their height (or, with
a wheelchair or mobility scooter, a level of their device); deeper water is never routed through,
and shallower water costs more the closer it is to that limit.

## Walkthrough

Each trip opens with the next step to take, and the map highlights the route it refers to. Water
the traveller can walk through is blue; water over their limit, or of unknown depth, is dashed red.
Every route shows its length, time, deepest water, and its steepest and gentlest gradient where the
City of Melbourne has measured the footpaths.
The sources behind every flood level and depth limit, and which values are judgements, are on the
`/reference` page, reached only by its address.

**Flood levels.** From none to extreme: the typical water on flooded footpaths rises from the
ankle (6 cm) to the calf (32 cm), the thigh (54 cm) and above the hip (99 cm).

![The water on the map rising from light to extreme flooding](docs/images/flood-levels.gif)

**A route that fits, around the water.** Light flooding, ankle limit: the shortest way crosses
water of unknown depth, so the recommended route walks 12 m further to stay within the limit.

![The recommended route, then the flood-ignoring shortest way it avoids](docs/images/detour.gif)

**No route fits: a choice.** Moderate flooding, Boyd Village to Crown Melbourne, mid-calf limit
(28 cm): every way crosses at least 32 cm, so the choices are to accept water up to the knee or to
stay inside. Taking the knee limit gives a route.

![Two choices, then the route with the knee limit](docs/images/choose.gif)

**Go to a shelter.** Heavy flooding, from dry ground: every way to the destination crosses at
least 68 cm, more than the 50 cm anyone is routed through, so the next step is the nearest shelter,
140 m away and dry all the way.

![The way to the nearest shelter when the destination is out of reach](docs/images/shelter.gif)

**Standing in deep water.** Heavy flooding, starting in 67 cm: emergency help comes first, then the
nearest shelter by the shallowest way out.

![Emergency help and the shallowest way to shelter from deep water](docs/images/deep-water.gif)

**Cut off inside a building.** Extreme flooding, inside Boyd Village: every way to Crown Melbourne
crosses at least 147 cm. Staying inside is the advice, and emergency help is available, with a
reminder to move to a higher floor if water comes in.

![Emergency help for a traveller cut off by deep water inside a building](docs/images/cut-off.gif)

**With a wheelchair.** Light flooding, a manual wheelchair at its lowest level (no water, 2 cm),
from inside the Crown Entertainment Complex to Boyd Village: every step-free way crosses 3 cm, so
the choices are the device's next level, below a 4-inch castor axle (5 cm), or staying inside.
Each device has its own levels and cap (manual wheelchair 7.5 cm, powered wheelchair 5 cm,
mobility scooter 2.5 cm), and routes never use steps or footpaths measured steeper than 1:14.

![The next level of the device, then the step-free route with it](docs/images/wheelchair.gif)

**Steep paths.** No flooding, on the promenade between Southgate Avenue and Southbank Boulevard:
on foot the route is 109 m and climbs a path at 8.3% (1 in 12.1). With a manual wheelchair it goes
round that path, 429 m, and its steepest part is 6.9% (1 in 14.5), within the 1:14 (7.1%) limit for
wheelchairs and scooters.

![The route on foot over an 8.3% path, then the wheelchair route around it](docs/images/steep-path.gif)

**Help at any time.** A Get help button stays on the map, whatever the trip says: call 000 if
anyone's life is in danger, VICSES 132 500 for flood or storm help, or alert people nearby (the
alert is simulated, with a few seconds to undo it).

![Get help: calls to 000 and VICSES, and an SOS alert with undo](docs/images/get-help.gif)

**On a phone.** The map sits above a sheet that slides up; the legend starts folded.

<img src="docs/images/phone.gif" alt="A choice on a phone, with the sheet slid up" width="300">

## Repository layout

```
backend/                 Python package, scripts and tests (uv project)
  src/floodroute/        routing engine — see docs/architecture.md
    api/                 HTTP API for the web client (FastAPI)
  scripts/               data pipeline: download, build, validate
  tests/
  streamlit_app.py       Streamlit map UI, kept alongside the web client
frontend/                web client: React, TypeScript and MapLibre; phones and desktops
data/                    raw downloads and processed networks (git-ignored, rebuilt by scripts);
                         data/scenarios/ holds the flood scenario definitions (JSON)
docs/                    architecture, parameters and their basis, verification
```

## Getting started

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/); the web client also needs Node.js 20.

```bash
cd backend
uv sync                                    # create .venv and install dependencies
uv run python scripts/download_data.py     # fetch OSM, City of Melbourne, terrain, overlay and drain data into data/raw
uv run python scripts/build_network.py     # build data/processed/southbank_network.gpkg and places
uv run python scripts/make_scenarios.py    # build the flood scenario depth grids into data/processed
uv run pytest                              # run the test suite
uv run ruff check && uv run ruff format --check  # lint and formatting
uv run python scripts/compare_pathfinders.py  # verify the in-house Dijkstra against NetworkX
uv run python scripts/verify.py            # cases A–J vs the predictions in docs/verification.md
uv run streamlit run streamlit_app.py      # open the Streamlit map UI
```

The web application:

```bash
cd frontend && npm install && npm run build   # build the web client into frontend/dist
cd ../backend && uv run uvicorn floodroute.api.app:app --port 8000
```

then open http://localhost:8000; the API serves the built client and its own routes under
`/api` (interactive reference at http://localhost:8000/docs). The data sources, documents and
the basis of every depth limit are at http://localhost:8000/reference, a page the app does not
link to. While working on the client, run
`npm run dev` in `frontend/` instead and open the address it prints; it passes `/api` requests to
the API on port 8000 (or wherever `FLOODROUTE_API_URL` points, e.g. `http://127.0.0.1:8010` when
port 8000 is taken) and reloads on every change.

### Sharing a temporary public link

To let someone elsewhere open your copy, without hosting it anywhere, run from the repository root

```bash
./deploy/share.sh       # macOS and Linux; on Windows double-click deploy\share.bat
```

Each run builds the web client from your working copy, starts the API on a free local port
(8010, or the next free one) and opens a [Cloudflare quick tunnel](https://try.cloudflare.com),
then prints a public `https://….trycloudflare.com` address with a QR code of it, in the terminal
and as `deploy/share.png`, for opening it on a phone. Ctrl+C stops both and deletes the image
(closing the window on Windows also stops them; an image left behind is deleted on the next run).
It needs the processed data from the steps above, Node.js, and `cloudflared` (`brew install
cloudflared` on macOS, `winget install --id Cloudflare.cloudflared` on Windows).
The address is public, so anyone who has it can open the app; it changes on every run and works
only while your computer is on and the script is running. It serves your local files, so pull
first if you want the latest commits.

`scripts/build_network.py --source com` builds the alternative City of Melbourne network, and
`scripts/validate_com_network.py` reports its topology and coverage against OpenStreetMap.
Both write maps and reports to `reports/` (git-ignored).

## How to test

Testing works on two layers. Whether the **algorithms** follow their rules on the data they are
given is checked automatically, on made-up data and on the real network. Whether the **data**
matches the streets can only be checked on site. Every check below has its predictions written
before it was first run ([docs/verification.md](docs/verification.md),
[docs/benchmarks.md](docs/benchmarks.md)); the latest results are on the `/benchmark` page,
reached only by its address.

### 1. Pedestrian safety

Approach: scenario-based algorithm testing and quantitative evaluation. It verifies that routes
avoid water over the traveller's limit throughout a trip, that trips are planned again correctly
when conditions change, and that the safety constraints hold under simulated flood events.

- **Scenario tests (made-up data).** A small test town, cases A–J: every prediction is worked out
  by hand before the program runs, and 130 of 130 are met. Case F checks that switching between
  normal and flood conditions gives the right plan each time.
- **Quantitative evaluation (real data).** 100 random Southbank trips at each of the 5 flood levels,
  checked against properties R-A to R-I, with 0 violations: for example, no route crosses water
  over the traveller's limit, a looser limit never makes fewer trips possible, and wheelchair
  routes never use steps or paths steeper than 1:14.
- **Benchmarks.** Rerouting while the flood rises during a walk, planned again from where the
  traveller is; the safety each route gives and what it costs (detour, water avoided) at each
  level for several travellers; and fault injection, which breaks each safety rule on purpose to
  show that the tests catch it.

### 2. Public area accessibility

Approach: scenario-based algorithm testing, quantitative evaluation and on-site route inspection
(ground truthing). It verifies that routes are accessible as computed, and assesses on site how
connected the paths really are, physical barriers, and access to public building entrances.

- **Algorithm (automated).**
  - Cases G (steps), H (wheelchair and scooter levels) and J (paths steeper than 1:14) in the test
    town, and R-G and R-I on Southbank (no wheelchair route uses steps or a steep path).
  - The share of pairs of buildings with a step-free route between them.
  - How much longer the step-free route is than the walking route.
- **Data (on site only).** The repository provides the tools; the inspection is done by people:
  - a sampling script draws footpath sections, by kind (steep paths among them), and building
    entrances from the model;
  - a checklist (CSV): steps, kerb ramps, gradient, width, barriers or closures, whether entrances
    are step-free and open to the public, with photos;
  - a comparison script reads the completed checklist, compares it with the model and gives the
    agreement; above all the share of items the model treats as usable that are not on site, the
    most dangerous kind of error.

```bash
cd backend
uv run pytest                                 # unit tests and the test town cases
uv run python scripts/verify.py               # every hand-derived prediction, incl. Southbank
uv run python scripts/benchmark.py            # all benchmarks -> docs/benchmark.json and /benchmark
uv run python scripts/ground_truth_sample.py  # checklist to inspect -> data/ground_truth/sample.csv
uv run python scripts/ground_truth_compare.py ../data/ground_truth/inspected.csv
```

## Data sources

| Data | Source | Licence |
|---|---|---|
| Walking network, buildings, entrances | © OpenStreetMap contributors, via Overpass API / osmnx | ODbL |
| Southbank boundary (study area) | City of Melbourne, CLUE small areas | CC BY |
| Pedestrian network (alternative source) | City of Melbourne, Pedestrian Network | CC BY |
| Place search | OpenStreetMap Nominatim | ODbL; usage policy applies |
| Ground elevation | Geoscience Australia, 5 m LiDAR DEM (2025) | CC BY 4.0 |
| Flood overlays (LSIO, SBO, FO) | Vicmap Planning, Department of Transport and Planning | CC BY 4.0 |
| Stormwater pits | City of Melbourne, Stormwater Pits | CC BY |
| Footpath gradients | City of Melbourne, Footpath steepness | CC BY |
| Flood mechanisms, tide levels and checks | Melbourne Water Southbank Local Floodplain Development Plan (2026); GHD for Melbourne Water (2017); Port Phillip Bay Coastal Hazard Assessment (2023); City of Melbourne flood and storm sub-plan (2025); VICSES Southbank Local Flood Guide (2021) | cited, not redistributed |
| Flood level boundaries | Feng, Brenner & Sester (2020); Drillis & Contini (1966); Smith, Davey & Cox (2014); ABS Australian Health Survey 2011–12 | cited |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, branch and commit conventions, and checks to run
before opening a pull request.

## Safety notice

Routes are guidance based on modelled or reported conditions, which can be incomplete, out of date
or wrong, and flood conditions can change quickly. A suggested route is not a guarantee that it is
safe. Never walk, ride or drive through floodwater you do not have to, follow directions from
emergency services, and in an emergency call 000; for flood or storm help, call VICSES on 132 500.

## Licence

Code is licensed under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for attribution.
Data listed above keeps its own licence; processed network files derived from OpenStreetMap are
covered by the ODbL and must credit OpenStreetMap if shared.
