"""The languages the API answers in, and the sentences it composes in each.

Every text the API sends for people to read (labels, depth descriptions, the route preference
example, route names, error messages, scenario titles, descriptions and source notes) is looked
up here by a stable key and filled in with its values. The engine hands the API values and keys rather than
wording (``risk.profile.depth_reach``, ``risk.preference.example``, ``RoutingError.key``,
``AccessPoint.kind``); its English sentences remain for its own reports and the Streamlit app,
and the English catalogue says the same (tests/test_i18n.py checks both).

Catalogues are ``locales/<language>.json``: one flat object per language, with the same keys and
the same ``{placeholders}`` in every language. Scenario text in English comes from the scenario
files (``data/scenarios``); the other languages carry titles and descriptions as
``scenario.<id>.title`` and ``scenario.<id>.description``, and each source note as
``scenario.source.<the English note>``, since most notes are shared by several scenarios. Numbers,
units, phone numbers and place names are written the same in every language (see
docs/languages.md).
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from floodroute.hazard.catalog import ScenarioInfo
from floodroute.places.resolver import AccessPoint
from floodroute.risk.preference import example
from floodroute.risk.profile import TravellerProfile, depth_reach

LANGUAGES = ("en", "es", "zh-Hans", "hi", "ko")
DEFAULT_LANGUAGE = "en"
LOCALES_DIR = Path(__file__).with_name("locales")
# The offered language for a tag's primary subtag. Chinese is offered in one written form,
# Simplified, for every Chinese tag (Mandarin and Cantonese speakers alike).
_BY_PRIMARY = {"en": "en", "es": "es", "zh": "zh-Hans", "hi": "hi", "ko": "ko"}


@cache
def catalogue(language: str) -> dict[str, str]:
    return json.loads((LOCALES_DIR / f"{language}.json").read_text(encoding="utf-8"))


def text(language: str, key: str, /, **values: object) -> str:
    """The sentence ``key`` in ``language``, filled in with ``values``; English when the language
    has no such sentence."""
    template = catalogue(language).get(key) or catalogue(DEFAULT_LANGUAGE)[key]
    return template.format(**values)


def offered(tag: str | None) -> str | None:
    """The offered language a BCP 47 tag asks for, if any: "es-AR" is Spanish, "zh-TW" Chinese."""
    if not tag:
        return None
    return _BY_PRIMARY.get(tag.strip().split("-")[0].split("_")[0].lower())


def negotiate(requested: str | None = None, accept_language: str | None = None) -> str:
    """The language to answer in: ``requested`` (the ``lang`` parameter) if it is offered, else the
    most preferred offered language in an Accept-Language header, else English."""
    if chosen := offered(requested):
        return chosen
    ranked = []
    for i, item in enumerate((accept_language or "").split(",")):
        tag, _, params = item.partition(";")
        q = 1.0
        for param in params.split(";"):
            name, _, value = param.partition("=")
            if name.strip() == "q":
                try:
                    q = float(value)
                except ValueError:
                    q = 0.0
        if q > 0 and (language := offered(tag)):
            ranked.append((-q, i, language))
    return min(ranked)[2] if ranked else DEFAULT_LANGUAGE


# ---------------------------------------------------------------------- engine values in words


def _key(words: str) -> str:
    return words.replace(" ", "_")


def depth_label(language: str, depth_m: float | None, height_m: float) -> str:
    """Where water of this depth reaches on this person, e.g. "up to the ankle"."""
    return text(language, f"depth.{_key(depth_reach(depth_m, height_m))}")


def limit_label(language: str, profile: TravellerProfile) -> str:
    """The traveller's limit in words: a level of their device, or where it reaches on the body."""
    if profile.aid is not None:
        return text(language, f"aid_level.{profile.aid.key}")
    return depth_label(language, profile.depth_limit_m, profile.height_m)


def explanation(language: str, alpha: float, profile: TravellerProfile) -> str:
    """What a risk weight means for this traveller, as an example in metres."""
    ex = example(alpha, profile)
    if ex is None:
        return text(language, "explanation.no_water")
    return text(
        language,
        "explanation.example",
        water=f"{ex.water_m:.0f}",
        depth=f"{ex.depth_m * 100:.0f}",
        reach=depth_label(language, ex.depth_m, profile.height_m),
        detour=ex.detour_m,
    )


def access_label(language: str, access: AccessPoint) -> str:
    """Where a route joins a place, e.g. "main entrance" or "entrance (Riverside)"."""
    kind = text(language, f"access.{access.kind}")
    return text(language, "access.named", access=kind, name=access.name) if access.name else kind


def scenario_text(language: str, info: ScenarioInfo) -> tuple[str, str]:
    """A scenario's title and description."""
    words = catalogue(language) if language != DEFAULT_LANGUAGE else {}
    return (
        words.get(f"scenario.{info.id}.title", info.title),
        words.get(f"scenario.{info.id}.description", info.description),
    )


def scenario_sources(language: str, info: ScenarioInfo) -> list[str]:
    """Where a scenario's values come from, one note per source. Document and dataset titles, names,
    years and licences in a note stay as published."""
    words = catalogue(language) if language != DEFAULT_LANGUAGE else {}
    return [words.get(f"scenario.source.{note}", note) for note in info.params.get("sources", [])]
