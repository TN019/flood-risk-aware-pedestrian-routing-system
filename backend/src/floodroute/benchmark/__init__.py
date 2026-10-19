"""Benchmarks of the routing engine, and a kit for inspecting its data on site.

- ``correctness``: the path finders against a reference and brute force.
- ``faults``: safety rules broken on purpose, to show the test suite notices.
- ``safety``: the safety routes give and what it costs, and rerouting while a flood rises.
- ``access``: step-free connectivity between buildings.
- ``ground_truth``: a stratified sample to inspect on site, and the comparison with the model.

``scripts/benchmark.py`` runs them on the Southbank network; docs/benchmarks.md states what each
should show, written before the first run.
"""
