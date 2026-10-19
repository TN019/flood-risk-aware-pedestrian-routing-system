import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, api } from "./api";
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

const DEFAULT_TRAVELLER: Traveller = {
  height_cm: 170,
  wading: "ankle",
  mobility_aid: "none",
  aid_level: 0,
  preference: "balanced",
  alpha: null,
};

export default function App() {
  const [area, setArea] = useState<Area | null>(null);
  const [network, setNetwork] = useState<FeatureCollection | null>(null);
  const [options, setOptions] = useState<Options | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

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
  const [notice, setNotice] = useState<string | null>(null);
  const [sos, setSos] = useState<SosState | null>(null);
  const [selected, setSelected] = useState<RouteKind | null>(null);
  const [focus, setFocus] = useState(0);
  const [sheetOpen, setSheetOpen] = useState(false);
  const panelRef = useRef<HTMLElement>(null);
  const shownEnds = useRef("");

  // Static data, once.
  useEffect(() => {
    Promise.all([api.area(), api.options(), api.scenarios()])
      .then(([a, o, s]) => {
        setArea(a);
        setOptions(o);
        setScenarios(s);
        setScenarioId(s[0]?.id ?? null);
      })
      .catch((err) => setLoadError(err instanceof ApiError ? err.message : "Could not load the map data."));
    api.network().then(setNetwork).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!scenarioId || water[scenarioId]) return;
    api
      .water(scenarioId)
      .then((fc) => setWater((w) => ({ ...w, [scenarioId]: fc })))
      .catch(() => undefined);
  }, [scenarioId, water]);

  useEffect(() => {
    const controller = new AbortController();
    api
      .traveller(traveller, controller.signal)
      .then(setInfo)
      .catch(() => undefined);
    return () => controller.abort();
  }, [traveller]);

  // Plan whenever anything the plan depends on changes.
  useEffect(() => {
    if (!start || !destination || !scenarioId) {
      setTrip(null);
      setTripError(null);
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setPlanning(true);
      api
        .trip(start, destination, scenarioId, traveller, controller.signal)
        .then((t) => {
          setTrip(t);
          setSelected(defaultChoice(t));
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
          setTripError(err instanceof ApiError ? err.message : "Could not plan this trip.");
        })
        .finally(() => setPlanning(false));
    }, 150);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [start, destination, scenarioId, traveller]);

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
        setNotice("Pick a point inside Southbank (the black boundary).");
        return;
      }
      setPoint(clickTarget, { lat, lon, label: null, footprint: null, source: "map" });
    },
    [clickTarget, inside, setPoint],
  );

  const pick = (which: Which) => (hit: SearchHit) => {
    if (!inside(hit.lat, hit.lon)) {
      setNotice(`${hit.label.split(",")[0]} is outside Southbank.`);
      return;
    }
    setPoint(which, { lat: hit.lat, lon: hit.lon, label: hit.label.split(",")[0], footprint: hit.footprint, source: "search" });
  };

  const locate = () => {
    if (!navigator.geolocation) {
      setNotice("Location is not available in this browser. Click the map to set your start instead.");
      return;
    }
    setNotice("Finding your location…");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude: lat, longitude: lon } = pos.coords;
        if (!inside(lat, lon)) {
          setNotice("Your location is outside Southbank. Click the map to set a simulated current location instead.");
          return;
        }
        setPoint("start", { lat, lon, label: "Your location", footprint: null, source: "location" });
      },
      () => setNotice("Location unavailable (permission denied or not supported). Click the map to set your start instead."),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  const scenario = useMemo(() => scenarios.find((s) => s.id === scenarioId) ?? null, [scenarios, scenarioId]);
  const depthLimit = info?.depth_limit_m ?? 0.02;

  if (loadError) {
    return (
      <div className="fatal">
        <h1>Southbank Flood Routes</h1>
        <p>{loadError}</p>
      </div>
    );
  }

  return (
    <div className="app">
      <aside ref={panelRef} className={`panel ${sheetOpen ? "panel-open" : ""}`} aria-label="Trip planner">
        <button type="button" className="sheet-handle" onClick={() => setSheetOpen((o) => !o)} aria-expanded={sheetOpen}>
          <span />
          {sheetOpen ? "Show more map" : "Show details"}
        </button>
        <header className="brand">
          <h1>Southbank Flood Routes</h1>
          <p>Walking routes that avoid water deeper than you choose to walk through.</p>
        </header>

        <section className="card trip-card" aria-label="Start and destination">
          <PlaceSearch
            label="Start"
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
                ◎ Use my current location
              </button>
            }
          />
          <PlaceSearch
            label="Destination"
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
              ⇅ Swap
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
              Clear
            </button>
          </div>
          {notice && <p className="hint">{notice}</p>}
          {!start && !destination && !notice && (
            <p className="hint">Search for a place, or click the map: the first click sets the start, the next the destination.</p>
          )}
        </section>

        {planning && <p className="planning" role="status">Planning…</p>}
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
          <p>
            Routes are guidance based on modelled conditions, which can be incomplete or wrong, and floods change quickly. Never walk
            through floodwater you do not have to, follow directions from emergency services, and in an emergency call 000.
          </p>
          <p>Map data © OpenStreetMap contributors. Flood scenarios: see Sources under each level.</p>
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
          Next click sets the <strong>{clickTarget}</strong>
        </div>
      </main>
    </div>
  );
}
