# Flood Risk-Aware Pedestrian Routing

Walking routes for Southbank, Melbourne that minimise exposure to flood hazards instead of only
distance. The routing engine works on a real pedestrian network; flood conditions come from
interchangeable sources (synthetic scenarios today, sensors and forecasts later). Each traveller
sets the deepest water they accept as a body part, converted to a depth from their height; deeper
water is never routed through, and shallower water costs more the closer it is to that limit.

## Repository layout

```
backend/                 Python package, scripts and tests (uv project)
  src/floodroute/        routing engine — see docs/architecture.md
  scripts/               data pipeline: download, build, validate
  tests/
  streamlit_app.py       interim map UI, to be replaced by frontend/
frontend/                web client (planned)
data/                    raw downloads and processed networks (git-ignored, rebuilt by scripts);
                         data/scenarios/ holds synthetic flood scenarios (GeoJSON)
docs/                    architecture and design notes
```

## Getting started

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync                                    # create .venv and install dependencies
uv run python scripts/download_data.py     # fetch OSM and City of Melbourne data into data/raw
uv run python scripts/build_network.py     # build data/processed/southbank_network.gpkg and places
uv run pytest                              # run the test suite
uv run python scripts/compare_pathfinders.py  # verify the in-house Dijkstra against NetworkX
uv run streamlit run streamlit_app.py      # open the interim map UI
```

`scripts/build_network.py --source com` builds the alternative City of Melbourne network, and
`scripts/validate_com_network.py` reports its topology and coverage against OpenStreetMap.
Both write maps and reports to `reports/` (git-ignored).

## Data sources

| Data | Source | Licence |
|---|---|---|
| Walking network, buildings, entrances | © OpenStreetMap contributors, via Overpass API / osmnx | ODbL |
| Southbank boundary (study area) | City of Melbourne, CLUE small areas | CC BY |
| Pedestrian network (alternative source) | City of Melbourne, Pedestrian Network | CC BY |
| Place search | OpenStreetMap Nominatim | ODbL; usage policy applies |
