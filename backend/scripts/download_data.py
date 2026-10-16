"""Download the raw input data into data/raw/.

Run:  uv run python scripts/download_data.py [--only osm|buildings|context|com|boundary ...]

- osm        OpenStreetMap walking network (unsimplified GraphML)
- buildings  OpenStreetMap building footprints and entrances
- context    OpenStreetMap water and bridges (used by scripts/validate_com_network.py)
- com        City of Melbourne pedestrian network (alternative network source)
- boundary   City of Melbourne CLUE Southbank boundary (study area)
"""

from __future__ import annotations

import argparse

from floodroute.sources import com, osm

STEPS = {
    "boundary": com.download_clue_boundary,
    "osm": osm.download_walk_network,
    "buildings": osm.download_buildings,
    "context": osm.download_water_and_bridges,
    "com": com.download_pedestrian_network,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", nargs="+", choices=sorted(STEPS), help="download only these datasets")
    args = parser.parse_args()
    for name in args.only or STEPS:
        print(f"{name:10s} ->", STEPS[name]())


if __name__ == "__main__":
    main()
