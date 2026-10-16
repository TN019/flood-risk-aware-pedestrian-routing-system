"""Flood risk-aware pedestrian routing.

Layers, bottom up: ``sources`` (external data) → ``network`` (routing graph) → ``hazard`` (flood
conditions) → ``risk`` (costs and limits) → ``routing`` (path search); ``places`` resolves where a
walk starts and ends, and ``prediction`` holds forecasting models.
"""

__version__ = "0.1.0"
