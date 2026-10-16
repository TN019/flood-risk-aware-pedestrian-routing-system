"""Flood forecasting models.

A ``Predictor`` estimates future water conditions on network edges from past and current
observations (rainfall, river level, sensor depths, ...). Models are trained and evaluated
offline; a trained model reaches routing through a ``HazardProvider`` that turns its forecasts
into ``HazardSnapshot``s, so models can be replaced or run side by side (a primary model and a
challenger) without changing routing code.

No model is included yet. Planned families, each implementing ``Predictor``: linear regression,
conditional Markov chains over hazard states, and neural networks.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol

import pandas as pd

from floodroute.hazard import HazardSnapshot


class Predictor(Protocol):
    name: str

    def fit(self, observations: pd.DataFrame) -> None:
        """Train on historical observations (one row per edge or sensor per time step)."""
        ...

    def predict(self, observations: pd.DataFrame, at: datetime, horizon: timedelta) -> HazardSnapshot:
        """Forecast conditions ``horizon`` after ``at`` given observations up to ``at``."""
        ...


__all__ = ["Predictor"]
