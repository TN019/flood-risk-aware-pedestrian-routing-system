"""HTTP API for the web client.

Run (from backend/):  uv run uvicorn floodroute.api.app:app --reload

All routes live under ``/api``. When the web client has been built (``frontend/dist``), it is
served from ``/`` as well, so one process serves the whole application.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from floodroute import config
from floodroute.api.service import RequestError, Service

BodyPartKey = Literal["no_wading", "ankle", "lower_calf", "mid_calf", "knee"]
PreferenceKey = Literal["shortest", "balanced", "avoid_water", "driest"]
CLIENT_DIR = config.REPO_ROOT / "frontend" / "dist"


class Traveller(BaseModel):
    height_cm: float = Field(170, ge=60, le=230)
    wading: BodyPartKey = "ankle"
    wheelchair: bool = False
    preference: PreferenceKey = "balanced"
    alpha: float | None = Field(None, ge=0, le=50, description="Overrides the preference's risk weight")


class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    label: str | None = Field(None, max_length=200)
    footprint: dict | None = Field(None, description="GeoJSON polygon of a searched place, WGS84")


class TripRequest(BaseModel):
    start: Location
    destination: Location
    scenario_id: str
    traveller: Traveller = Traveller()


def create_app(load_service: Callable[[], Service] = Service.from_files, serve_client: bool = True) -> FastAPI:
    holder: dict[str, Service] = {}

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        holder["service"] = load_service()
        yield
        holder.clear()

    app = FastAPI(title="Southbank flood-aware walking routes", lifespan=lifespan)

    def service() -> Service:
        return holder["service"]

    @app.exception_handler(RequestError)
    async def request_error(_, exc: RequestError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/area")
    def area() -> dict:
        return service().area()

    @app.get("/api/network")
    def network() -> dict:
        return service().network()

    @app.get("/api/options")
    def options() -> dict:
        return service().options()

    @app.get("/api/scenarios")
    def scenarios() -> list[dict]:
        return service().scenario_list()

    @app.get("/api/scenarios/{scenario_id}/water")
    def water(scenario_id: str) -> dict:
        if scenario_id not in service().scenarios:
            raise HTTPException(404, f"Unknown flood scenario {scenario_id!r}.")
        return service().water(scenario_id)

    @app.post("/api/traveller")
    def traveller(body: Traveller) -> dict:
        return service().traveller(body.height_cm, body.wading, body.wheelchair, body.preference, body.alpha)

    @app.get("/api/search")
    def search(q: str = Query(min_length=1, max_length=200)) -> list[dict]:
        try:
            return service().search(q)
        except RequestError:
            raise
        except Exception as exc:  # place search depends on an outside service
            raise HTTPException(502, "Place search is unavailable right now. Click the map instead.") from exc

    @app.post("/api/trip")
    def trip(body: TripRequest) -> dict:
        t = body.traveller
        return service().plan(
            body.start.model_dump(),
            body.destination.model_dump(),
            body.scenario_id,
            t.height_cm,
            t.wading,
            t.wheelchair,
            t.preference,
            t.alpha,
        )

    if serve_client and CLIENT_DIR.exists():
        app.mount("/", StaticFiles(directory=CLIENT_DIR, html=True), name="client")
    return app


app = create_app()
