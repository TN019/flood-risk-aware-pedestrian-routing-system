import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, errorText } from "./api";
import { ConditionsPanel } from "./components/ConditionsPanel";
import { GetHelp } from "./components/GetHelp";
import { MapLegend } from "./components/MapLegend";
import { MapView } from "./components/MapView";
import { PlaceSearch } from "./components/PlaceSearch";
import type { SosState } from "./components/Sos";
import { TravellerPanel } from "./components/TravellerPanel";
import { TripResults } from "./components/TripResults";
import { contains } from "./format";
import { defaultChoice } from "./guidance";
import { LanguageSwitcher, useDocumentTitle, useI18n } from "./i18n/I18n";
import type { MessageKey } from "./i18n/messages/en";
import type { Values } from "./i18n/translate";
import type { RouteKind } from "./routeStyles";
import type {
  Area,
  ChosenPoint,
  FeatureCollection,
  Options,
  ScenarioSummary,
  SearchHit,
  Traveller,
  TravellerInfo,
  TripPlan,
} from "./types";

type Which = "start" | "destination";

/** A message to the traveller, kept as a key so it follows a change of language. */
type Notice = { key: MessageKey; values?: Values };

const DEFAULT_TRAVELLER: Traveller = {
  height_cm: 170,
  wading: "ankle",
  mobility_aid: "none",
  aid_level: 0,
  preference: "balanced",
  alpha: null,
};

export default function App() {
  const { lang, t, rich } = useI18n();
  useDocumentTitle("app.title");
  const [area, setArea] = useState<Area | null>(null);
  const [network, setNetwork] = useState<FeatureCollection | null>(null);
  const [options, setOptions] = useState<Options | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const loaded = useRef(false);

  const [scenarioId, setScenarioId] = useState<string | null>(null);
  const [water, setWater] = useState<Record<string, FeatureCollection>>({});
  const [start, setStart] = useState<ChosenPoint | null>(null);
  const [destination, setDestination] = useState<ChosenPoint | null>(null);
  const [clickTarget, setClickTarget] = useState<Which>("start");
  const [traveller, setTraveller] = useState<Traveller>(DEFAULT_TRAVELLER);
  const [info, setInfo] = useState<TravellerInfo | null>(null);

  const [trip, setTrip] = useState<TripPlan | null>(null);
  const [tripError, setTripError] = useState<string | null>(null);
  const [planning, setPlanning] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [sos, setSos] = useState<SosState | null>(null);
  const [selected, setSelected] = useState<RouteKind | null>(null);
  const [focus, setFocus] = useState(0);
  const [sheetOpen, setSheetOpen] = useState(false);
  const panelRef = useRef<HTMLElement>(null);
  const shownEnds = useRef("");
  const plannedFor = useRef(""); // what the shown plan was asked for, apart from its language

  // The map data once (it has no text); the options and scenarios again in each language chosen.
  useEffect(() => {
    api.area(lang).then(setArea).catch((err) => setLoadError(errorText(err, t, t("app.loadError"))));
    api.network(lang).then(setNetwork).catch(() => undefined);
  }, []);

  useEffect(() => {
    Promise.all([api.options(lang), api.scenarios(lang)])
      .then(([o, s]) => {
        setOptions(o);
        setScenarios(s);
        setLoadError(null);
        if (!loaded.current) setScenarioId(s[0]?.id ?? null);
        loaded.current = true;
      })
      .catch((err) => {
        if (!loaded.current) setLoadError(errorText(err, t, t("app.loadError")));
      });
  }, [lang, t]);

  useEffect(() => {
    if (!scenarioId || water[scenarioId]) return;
    api
      .water(scenarioId, lang)
      .then((fc) => setWater((w) => ({ ...w, [scenarioId]: fc })))
      .catch(() => undefined);
  }, [scenarioId, water, lang]);

  useEffect(() => {
    const controller = new AbortController();
    api
      .traveller(traveller, lang, controller.signal)
      .then(setInfo)
      .catch(() => undefined);
    return () => controller.abort();
  }, [traveller, lang]);

  // Plan whenever anything the plan depends on changes; in another language, the same plan is
  // fetched again in its words, keeping the route shown.
  useEffect(() => {
    if (!start || !destination || !scenarioId) {
      setTrip(null);
      setTripError(null);
      return;
    }
    const controller = new AbortController();
    const asked = JSON.stringify([start, destination, scenarioId, traveller]);
    const timer = window.setTimeout(() => {
      setPlanning(true);
      const named = (p: ChosenPoint) => (p.label === null && p.source === "location" ? { ...p, label: t("trip.yourLocation") } : p);
      api
        .trip(named(start), named(destination), scenarioId, traveller, lang, controller.signal)
        .then((plan) => {
          setTrip(plan);
          if (asked !== plannedFor.current) setSelected(defaultChoice(plan));
          plannedFor.current = asked;
          setTripError(null);
          const ends = `${start.lat},${start.lon};${destination.lat},${destination.lon}`;
          if (ends !== shownEnds.current) {
            // New start or destination: bring the results into view, keeping the map visible.
            shownEnds.current = ends;
            window.requestAnimationFrame(() =>
              panelRef.current?.querySelector(".results")?.scrollIntoView({ behavior: "smooth", block: "start" }),
            );
          }
        })
        .catch((err) => {
          if ((err as Error).name === "AbortError") return;
          setTrip(null);
          plannedFor.current = "";
          setTripError(errorText(err, t, t("app.planError")));
        })
        .finally(() => setPlanning(false));
    }, 150);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [start, destination, scenarioId, traveller, lang, t]);

  useEffect(() => setSos(null), [start, destination]);

  const inside = useCallback((lat: number, lon: number) => !area || contains(area.study_area, lon, lat), [area]);

  const setPoint = useCallback(
    (which: Which, point: ChosenPoint) => {
      setNotice(null);
      if (which === "start") {
        setStart(point);
        if (!destination) setClickTarget("destination");
      } else {
        setDestination(point);
      }
    },
    [destination],
  );

  const onMapClick = useCallback(
    (lat: number, lon: number) => {
      if (!inside(lat, lon)) {
        setNotice({ key: "trip.outside" });
        return;
      }
      setPoint(clickTarget, { lat, lon, label: null, footprint: null, source: "map" });
    },
    [clickTarget, inside, setPoint],
  );

  const pick = (which: Which) => (hit: SearchHit) => {
    if (!inside(hit.lat, hit.lon)) {
      setNotice({ key: "trip.placeOutside", values: { place: hit.label.split(",")[0] } });
      return;
    }
    setPoint(which, { lat: hit.lat, lon: hit.lon, label: hit.label.split(",")[0], footprint: hit.footprint, source: "search" });
  };

  const locate = () => {
    if (!navigator.geolocation) {
      setNotice({ key: "trip.noGeolocation" });
      return;
    }
    setNotice({ key: "trip.locating" });
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude: lat, longitude: lon } = pos.coords;
        if (!inside(lat, lon)) {
          setNotice({ key: "trip.locationOutside" });
          return;
        }
        // No label of its own: it is named in the language shown (PlaceSearch, api.trip).
        setPoint("start", { lat, lon, label: null, footprint: null, source: "location" });
      },
      () => setNotice({ key: "trip.locationFailed" }),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  const scenario = useMemo(() => scenarios.find((s) => s.id === scenarioId) ?? null, [scenarios, scenarioId]);
  const depthLimit = info?.depth_limit_m ?? 0.02;

  if (loadError) {
    return (
      <div className="fatal">
        <div className="brand-row">
          <h1>{t("app.title")}</h1>
          <LanguageSwitcher />
        </div>
        <p>{loadError}</p>
      </div>
    );
  }

  return (
    <div className="app">
      <aside ref={panelRef} className={`panel ${sheetOpen ? "panel-open" : ""}`} aria-label={t("app.panel")}>
        <button type="button" className="sheet-handle" onClick={() => setSheetOpen((o) => !o)} aria-expanded={sheetOpen}>
          <span />
          {sheetOpen ? t("app.sheetMore") : t("app.sheetDetails")}
        </button>
        <header className="brand">
          <div className="brand-row">
            <h1>{t("app.title")}</h1>
            <LanguageSwitcher />
          </div>
          <p>{t("app.tagline")}</p>
        </header>

        <section className="card trip-card" aria-label={t("trip.label")}>
          <PlaceSearch
            label={t("trip.start")}
            value={start}
            active={clickTarget === "start"}
            onActivate={() => setClickTarget("start")}
            onPick={pick("start")}
            onClear={() => {
              setStart(null);
              setClickTarget("start");
            }}
            extra={
              <button type="button" className="link locate" onClick={locate}>
                ◎ {t("trip.locate")}
              </button>
            }
          />
          <PlaceSearch
            label={t("trip.destination")}
            value={destination}
            active={clickTarget === "destination"}
            onActivate={() => setClickTarget("destination")}
            onPick={pick("destination")}
            onClear={() => {
              setDestination(null);
              setClickTarget("destination");
            }}
          />
          <div className="trip-actions">
            <button
              type="button"
              className="link"
              disabled={!start && !destination}
              onClick={() => {
                setStart(destination);
                setDestination(start);
              }}
            >
              ⇅ {t("trip.swap")}
            </button>
            <button
              type="button"
              className="link"
              disabled={!start && !destination}
              onClick={() => {
                setStart(null);
                setDestination(null);
                setClickTarget("start");
              }}
            >
              {t("trip.clear")}
            </button>
          </div>
          {notice && <p className="hint">{t(notice.key, notice.values)}</p>}
          {!start && !destination && !notice && <p className="hint">{t("trip.hint")}</p>}
        </section>

        {planning && <p className="planning" role="status">{t("app.planning")}</p>}
        {tripError && <div className="alert alert-red" role="alert">{tripError}</div>}
        {trip && options && (
          <TripResults
            trip={trip}
            options={options}
            sos={sos}
            onSos={setSos}
            onUseLimit={(d) =>
              setTraveller((t) => (d.aid_level !== null ? { ...t, aid_level: d.aid_level } : { ...t, wading: d.body_part ?? t.wading }))
            }
            selected={selected}
            onSelect={(kind) => {
              setSelected(kind);
              if (kind) setFocus((f) => f + 1);
            }}
          />
        )}

        {options && scenarios.length > 0 && (
          <ConditionsPanel scenarios={scenarios} selected={scenario} options={options} onSelect={setScenarioId} />
        )}
        {options && <TravellerPanel options={options} traveller={traveller} info={info} onChange={setTraveller} />}

        <footer className="footnote">
          <p>{t("app.safety")}</p>
          <p>{t("app.credits")}</p>
        </footer>
      </aside>

      <main className="map-wrap">
        <MapView
          area={area}
          network={network}
          water={scenarioId ? water[scenarioId] ?? null : null}
          depthLimitM={depthLimit}
          heightM={traveller.height_cm / 100}
          options={options}
          trip={trip}
          start={start}
          destination={destination}
          onMapClick={onMapClick}
          selected={selected}
          focus={focus}
        />
        <MapLegend trip={trip} selected={selected} hasWater={!!scenarioId && (water[scenarioId]?.features.length ?? 0) > 0} />
        <GetHelp start={start} sos={sos} undoSeconds={options?.sos_undo_seconds ?? 5} onSos={setSos} />
        <div className="click-target" role="status">
          {rich("app.nextClick", { target: <strong key="target">{t(`app.nextClick.${clickTarget}`)}</strong> })}
        </div>
      </main>
    </div>
  );
}
