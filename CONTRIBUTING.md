# Contributing

Thanks for helping. This project suggests walking routes during floods, so correctness matters
more than speed of delivery: changes that affect which paths are allowed, or how risky they look,
need tests and a clear explanation.

## Set up

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/). All backend commands run from `backend/`.

```bash
cd backend
uv sync                                    # .venv with runtime, dev and tool dependencies
uv run python scripts/download_data.py     # raw OSM, City of Melbourne, terrain, overlay and drain data into data/raw
uv run python scripts/build_network.py     # processed network and places into data/processed
uv run python scripts/make_scenarios.py    # flood scenario depth grids into data/processed/scenarios
```

Downloads use public Overpass, City of Melbourne, Geoscience Australia and Vicmap endpoints; if an
Overpass mirror is busy the script tries the next one. Raw and processed data are not committed
(see `.gitignore`).

Read [docs/architecture.md](docs/architecture.md) before larger changes: it describes the layers
and the interfaces new code should plug into.

## Workflow

1. Branch from an up-to-date `main`, named `<type>/<short-description>`, e.g. `feat/flood-scenarios`,
   `fix/snapping-on-bridges`, `docs/api-usage`.
2. Make focused commits. Each commit message is one English sentence in
   [Conventional Commits](https://www.conventionalcommits.org/) form:

   ```
   <type>(<scope>): <what the commit does>
   ```

   Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `style`, `chore`, `ci`.
   Scope is the area touched, e.g. `routing`, `risk`, `hazard`, `network`, `places`, `scripts`.
   Example: `fix(routing): join endpoints to the path under a bridge when it is cheaper`.
3. Before pushing, make sure all of these pass:

   ```bash
   uv run ruff check . ../deploy           # lint (uv run ruff check --fix for safe automatic fixes)
   uv run ruff format --check . ../deploy  # formatting (uv run ruff format to apply)
   uv run pytest                           # tests
   ```

   If you change the web client, also run, from `frontend/`:

   ```bash
   npm run build                  # type check and production build
   npm test                       # unit tests
   ```

   If a change adds a feature or changes what the app shows, refresh the README images in the same
   pull request: with the API (port 8010) and `npm run dev` running, `npm run capture` rewrites the
   screenshots and the walkthrough in `docs/images/` (needs Google Chrome and ffmpeg).

   If you change path finding, also run `uv run python scripts/compare_pathfinders.py`; it must
   report no mismatches against the NetworkX reference.
4. Open a pull request into `main` describing what changed, why, and how it was verified.
   GitHub Actions runs the same lint, format and test commands on every pull request
   (`.github/workflows/ci.yml`), for the backend and for the web client. CI has no downloaded
   data, so the tests that need the processed Southbank network and flood grids skip there: run
   `uv run pytest` and `uv run python scripts/verify.py` locally with the data before asking for
   a merge.

## Code guidelines

- **Respect the layers.** `sources → network → hazard → risk → routing`; a layer must not import
  from one above it. New behaviour plugs in through the existing interfaces instead of special
  cases: `PathFinder` for search algorithms, `HazardProvider` for flood data, `RiskModel` / edge
  cost functions for risk, `Predictor` for forecasting models.
- **Units and coordinates.** Distances and depths are metres; geometry work uses GDA2020 / MGA
  zone 55 (`config.METRIC_CRS`). Convert to WGS84 only at the edges (input points, map output).
- **Unknown is not safe.** Missing hazard data must never be treated as dry water. An edge cost of
  `None` means impassable, and every path finder must honour it.
- **Safety-relevant changes need tests.** Anything that changes passability, depth limits or risk
  costs must come with tests showing the intended behaviour, and the pull request should say so
  explicitly.
- **Style.** Formatting and linting are enforced by ruff (configured in `backend/pyproject.toml`).
  Use type hints on public functions and a short docstring explaining *why* when the reason is
  not obvious from the code.
- **Sources in one place per audience.** A new or changed data source or cited document goes into
  the README's Data sources table, NOTICE (if its licence needs attribution), `docs/parameters.md`
  for the values it sets, and `frontend/src/reference/content.ts`, which the `/reference` page
  shows. Values on that page come from the API and need no edit.
- **No secrets or large data in git.** Never commit API keys or tokens. Processed network files
  derived from OpenStreetMap are covered by the ODbL; do not commit or publish them without
  following its attribution and share-alike terms.

## Licence

By contributing you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE), as described in section 5 of the licence.
