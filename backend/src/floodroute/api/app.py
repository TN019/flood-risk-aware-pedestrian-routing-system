"""HTTP API for the web client.

Run (from backend/):  uv run uvicorn floodroute.api.app:app --reload

All routes live under ``/api``. When the web client has been built (``frontend/dist``), it is
served from ``/`` as well, so one process serves the whole application.

Text for people to read comes in the language asked for: the ``lang`` query parameter, else the
Accept-Language header, else English (``api.i18n``). Responses say which in Content-Language.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from floodroute import config
from floodroute.api import i18n
from floodroute.api.service import RequestError, Service

BodyPartKey = Literal["no_wading", "ankle", "lower_calf", "mid_calf", "knee"]
PreferenceKey = Literal["shortest", "balanced", "avoid_water", "driest"]
MobilityAidKey = Literal["none", "manual_wheelchair", "powered_wheelchair", "mobility_scooter"]
CLIENT_DIR = config.REPO_ROOT / "frontend" / "dist"


class Traveller(BaseModel):
    height_cm: float = Field(170, ge=60, le=230)
    wading: BodyPartKey = "ankle"
    wheelchair: bool = Field(False, description="Without mobility_aid: a manual wheelchair, no water")
    mobility_aid: MobilityAidKey = "none"
    aid_level: int = Field(0, ge=0, le=5, description="Index into the device's levels, lowest first")
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


def negotiated(request: Request) -> str:
    """The language to answer in: ``lang`` if it is offered, else Accept-Language, else English."""
    return i18n.negotiate(request.query_params.get("lang"), request.headers.get("accept-language"))


def language(
    request: Request,
    lang: str | None = Query(None, description=f"Language of the text: {', '.join(i18n.LANGUAGES)}"),
) -> str:
    return i18n.negotiate(lang, request.headers.get("accept-language"))


Lang = Annotated[str, Depends(language)]


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

    @app.middleware("http")
    async def content_language(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Content-Language"] = negotiated(request)
            response.headers["Vary"] = "Accept-Language"
        return response

    @app.exception_handler(RequestError)
    async def request_error(request: Request, exc: RequestError):
        return JSONResponse(status_code=422, content={"detail": exc.message(negotiated(request))})

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
    def options(lang: Lang) -> dict:
        return service().options(lang)

    @app.get("/api/scenarios")
    def scenarios(lang: Lang) -> list[dict]:
        return service().scenario_list(lang)

    @app.get("/api/scenarios/{scenario_id}/water")
    def water(scenario_id: str, lang: Lang) -> dict:
        if scenario_id not in service().scenarios:
            raise HTTPException(404, i18n.text(lang, "error.unknown_scenario", id=repr(scenario_id)))
        return service().water(scenario_id)

    @app.post("/api/traveller")
    def traveller(body: Traveller, lang: Lang) -> dict:
        return service().traveller(
            body.height_cm,
            body.wading,
            body.wheelchair,
            body.preference,
            body.alpha,
            body.mobility_aid,
            body.aid_level,
            lang,
        )

    @app.get("/api/search")
    def search(lang: Lang, q: str = Query(min_length=1, max_length=200)) -> list[dict]:
        try:
            return service().search(q)
        except RequestError:
            raise
        except Exception as exc:  # place search depends on an outside service
            raise HTTPException(502, i18n.text(lang, "error.search_unavailable")) from exc

    @app.get("/api/benchmark")
    def benchmark(lang: Lang) -> dict:
        """The last benchmark results (scripts/benchmark.py), shown at /benchmark. A stored record,
        sent as written: the /benchmark page words its fixed vocabulary itself."""
        if not config.BENCHMARK_PATH.exists():
            raise HTTPException(404, i18n.text(lang, "error.no_benchmark"))
        return json.loads(config.BENCHMARK_PATH.read_text())

    @app.post("/api/trip")
    def trip(body: TripRequest, lang: Lang) -> dict:
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
            t.mobility_aid,
            t.aid_level,
            lang,
        )

    if serve_client and CLIENT_DIR.exists():
        app.mount("/", StaticFiles(directory=CLIENT_DIR, html=True), name="client")
    return app


app = create_app()
