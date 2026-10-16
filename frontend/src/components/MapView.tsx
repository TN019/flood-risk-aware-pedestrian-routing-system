import maplibregl, { type GeoJSONSource, type LngLatBoundsLike, type MapMouseEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { cm, describeDepth, groupRoutes } from "../format";
import type { Area, ChosenPoint, FeatureCollection, Options, RouteJson, TripPlan } from "../types";

// Free vector basemap built from OpenStreetMap data (no key needed).
const BASEMAP = "https://tiles.openfreemap.org/styles/positron";
// Used instead when the vector basemap cannot be loaded at all.
const FALLBACK_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      maxzoom: 19,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm", paint: { "raster-saturation": -0.6 } }],
};
const BASEMAP_TIMEOUT_MS = 8000;
// The vector basemap has detail up to zoom 14; stretching it much further crashes Safari's WebGL.
const OVERSCALE_ZOOM_LEVELS = 4;
// Safari drops the WebGL context (e.g. in background tabs). When it hands it back, MapLibre's
// restore keeps using buffers from the old context, which Safari rejects, and the map stays blank.
// So after a lost context the map is built again on a fresh canvas, once the page is visible. If the
// new map loses its context again soon after, rebuilding would only loop: the map shows a prompt
// to reload it instead.
const REBUILD_DELAY_MS = 300;
const STABLE_MS = 30_000; // an automatic rebuild must have lasted this long before another one

export const COLOURS = {
  path: "#4a6f94",
  water: "#1f78b4",
  overLimit: "#d62728",
  shortest: "#555555",
  safe_shortest: "#e6550d",
  recommended: "#7b2cbf",
  downgrade: "#b07cd8",
  refuge: "#2ca02c",
  start: "#1a9850",
  destination: "#d73027",
};

const EMPTY: FeatureCollection = { type: "FeatureCollection", features: [] };
const RANK = { shortest: 0, safe_shortest: 1, recommended: 2 } as const;

interface Props {
  area: Area | null;
  network: FeatureCollection | null;
  water: FeatureCollection | null;
  depthLimitM: number;
  heightM: number;
  options: Options | null;
  trip: TripPlan | null;
  start: ChosenPoint | null;
  destination: ChosenPoint | null;
  onMapClick: (lat: number, lon: number) => void;
}

function line(route: RouteJson, kind: string): GeoJSON.Feature {
  return { type: "Feature", properties: { kind }, geometry: route.geometry };
}

function routeFeatures(trip: TripPlan | null): FeatureCollection {
  if (!trip) return EMPTY;
  const features: GeoJSON.Feature[] = [];
  if (trip.refuge) features.push(line(trip.refuge.route, "refuge"));
  if (trip.downgrade) features.push(line(trip.downgrade.route, "downgrade"));
  if (trip.routes) {
    const groups = groupRoutes(trip.routes.options)
      .map((g) => ({ ...g, kind: g.kinds.reduce((a, b) => (RANK[b] > RANK[a] ? b : a)) }))
      .sort((a, b) => RANK[a.kind] - RANK[b.kind]);
    for (const g of groups) features.push(line(g.option.route!, g.kind));
    const recommended = trip.routes.options.find((o) => o.kind === "recommended")?.route;
    for (const leg of recommended?.access_legs ?? []) {
      features.push({ type: "Feature", properties: { kind: "leg" }, geometry: leg });
    }
  }
  return { type: "FeatureCollection", features };
}

function placeFeatures(trip: TripPlan | null): FeatureCollection {
  if (!trip) return EMPTY;
  const features: GeoJSON.Feature[] = [];
  for (const [role, place] of [
    ["start", trip.start],
    ["destination", trip.destination],
  ] as const) {
    if (place.building) features.push({ type: "Feature", properties: { role, label: place.label }, geometry: place.building });
    if (place.method !== "point") {
      for (const a of place.access) {
        features.push({
          type: "Feature",
          properties: { role, label: `${place.label}: ${a.label}` },
          geometry: { type: "Point", coordinates: [a.lon, a.lat] },
        });
      }
    }
  }
  if (trip.refuge) {
    features.push({ type: "Feature", properties: { role: "refuge", label: `Shelter: ${trip.refuge.name}` }, geometry: trip.refuge.building });
  }
  return { type: "FeatureCollection", features };
}

type Part = "area" | "network" | "water" | "limit" | "trip";
const ALL_PARTS: Part[] = ["area", "network", "water", "limit", "trip"];

function wrap(g: GeoJSON.Geometry): FeatureCollection {
  return { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: g }] };
}

/** Push the current data into the app's layers. Safe to call at any time: while a style is still
 * being (re)loaded it changes nothing, and the next style load calls it again with every part. */
function sync(m: maplibregl.Map, p: Props, parts: Part[], fitted: { current: boolean }): void {
  const source = (id: string) => m.getSource(id) as GeoJSONSource | undefined;
  try {
    for (const part of parts) {
      if (part === "area" && p.area) {
        source("area")?.setData(wrap(p.area.study_area));
        source("ring")?.setData(wrap(p.area.routable_area));
        const canvas = m.getCanvas();
        if (!fitted.current && canvas.clientWidth > 100 && canvas.clientHeight > 100) {
          const [w, s, e, n] = p.area.bounds;
          m.fitBounds([[w, s], [e, n]] as LngLatBoundsLike, { padding: 20, duration: 0 });
          fitted.current = true;
        }
      } else if (part === "network") {
        source("network")?.setData(p.network ?? EMPTY);
      } else if (part === "water") {
        source("water")?.setData(p.water ?? EMPTY);
      } else if (part === "limit" && m.getLayer("water-over")) {
        // Unknown depth (null or missing) counts as too deep.
        const depth: maplibregl.ExpressionSpecification = ["coalesce", ["get", "depth_m"], 99];
        m.setFilter("water-over", [">", depth, p.depthLimitM]);
        m.setFilter("water-ok", ["<=", depth, p.depthLimitM]);
      } else if (part === "trip") {
        source("routes")?.setData(routeFeatures(p.trip));
        source("places")?.setData(placeFeatures(p.trip));
      }
    }
  } catch {
    // The style is being (re)loaded; its load handler syncs everything again.
  }
}

function markerElement(kind: "start" | "destination"): HTMLElement {
  const el = document.createElement("div");
  el.className = `pin pin-${kind}`;
  el.setAttribute("aria-label", kind === "start" ? "Start" : "Destination");
  el.textContent = kind === "start" ? "A" : "B";
  return el;
}

export function MapView(props: Props) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markers = useRef<{ start?: maplibregl.Marker; destination?: maplibregl.Marker }>({});
  const clickHandler = useRef(props.onMapClick);
  const popupInfo = useRef({ limit: props.depthLimitM, height: props.heightM, options: props.options });
  // Bumped each time a style finishes parsing and the app layers have been (re)added to it.
  const [styleVersion, setStyleVersion] = useState(0);
  const [generation, setGeneration] = useState(0); // bumped to rebuild the map after a lost context
  const lastRebuild = useRef(0); // time of the last automatic rebuild
  const [failed, setFailed] = useState(false); // the map keeps losing its context
  const camera = useRef<{ center: [number, number]; zoom: number }>({ center: [144.962, -37.826], zoom: 14.5 });
  const latest = useRef(props);
  const fitted = useRef(false);
  latest.current = props;
  clickHandler.current = props.onMapClick;
  popupInfo.current = { limit: props.depthLimitM, height: props.heightM, options: props.options };

  useEffect(() => {
    if (!container.current) return;
    const m = new maplibregl.Map({
      container: container.current,
      style: BASEMAP,
      center: camera.current.center,
      zoom: camera.current.zoom,
      maxZoom: 19,
      experimentalZoomLevelsToOverscale: OVERSCALE_ZOOM_LEVELS,
      attributionControl: { compact: true },
    });
    map.current = m;
    let rebuildTimer: number | undefined;
    let rebuildPending = false;
    const rebuild = () => {
      if (document.visibilityState !== "visible") {
        document.addEventListener("visibilitychange", rebuild, { once: true });
        return;
      }
      lastRebuild.current = Date.now();
      setGeneration((g) => g + 1);
    };
    m.on("webglcontextlost", () => {
      if (rebuildPending) return;
      rebuildPending = true;
      const c = m.getCenter();
      camera.current = { center: [c.lng, c.lat], zoom: m.getZoom() };
      if (Date.now() - lastRebuild.current < STABLE_MS) {
        setFailed(true);
        return;
      }
      rebuildTimer = window.setTimeout(rebuild, REBUILD_DELAY_MS);
    });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    // The app's own layers are added as soon as the style is parsed, not on "load", which waits for
    // every basemap tile, font and icon: if any of those fail (blocked or offline), the flood map,
    // routes and map clicks must still work.
    let styleParsed = false;
    const addLayers = () => {
      styleParsed = true;
      if (m.getSource("area")) return;
      const add = (id: string) => m.addSource(id, { type: "geojson", data: EMPTY });
      ["ring", "area", "network", "water", "places", "routes"].forEach(add);
      m.addLayer({ id: "ring", type: "line", source: "ring", paint: { "line-color": "#777", "line-width": 1.5, "line-dasharray": [4, 4] } });
      m.addLayer({
        id: "network-margin",
        type: "line",
        source: "network",
        filter: ["==", ["get", "kind"], "margin_path"],
        paint: { "line-color": COLOURS.path, "line-width": 1.5, "line-opacity": 0.3 },
      });
      m.addLayer({
        id: "network-avoided",
        type: "line",
        source: "network",
        filter: ["==", ["get", "kind"], "avoided_road"],
        paint: { "line-color": "#999", "line-width": 1.5, "line-opacity": 0.6, "line-dasharray": [3, 3] },
      });
      m.addLayer({
        id: "network-path",
        type: "line",
        source: "network",
        filter: ["==", ["get", "kind"], "path"],
        paint: { "line-color": COLOURS.path, "line-width": ["interpolate", ["linear"], ["zoom"], 14, 1.2, 18, 3], "line-opacity": 0.65 },
      });
      m.addLayer({ id: "area", type: "line", source: "area", paint: { "line-color": "#111", "line-width": 2.5 } });
      m.addLayer({
        id: "water-ok",
        type: "line",
        source: "water",
        layout: { "line-cap": "round" },
        paint: { "line-color": COLOURS.water, "line-width": ["interpolate", ["linear"], ["zoom"], 14, 3, 18, 8], "line-opacity": 0.85 },
      });
      m.addLayer({
        id: "water-over",
        type: "line",
        source: "water",
        paint: {
          "line-color": COLOURS.overLimit,
          "line-width": ["interpolate", ["linear"], ["zoom"], 14, 3, 18, 8],
          "line-opacity": 0.9,
          "line-dasharray": [2, 1],
        },
      });
      m.addLayer({
        id: "place-fill",
        type: "fill",
        source: "places",
        filter: ["==", ["geometry-type"], "Polygon"],
        paint: {
          "fill-color": ["match", ["get", "role"], "start", COLOURS.start, "destination", COLOURS.destination, COLOURS.refuge],
          "fill-opacity": ["match", ["get", "role"], "refuge", 0.3, 0.15],
        },
      });
      m.addLayer({
        id: "place-outline",
        type: "line",
        source: "places",
        filter: ["==", ["geometry-type"], "Polygon"],
        paint: {
          "line-color": ["match", ["get", "role"], "start", COLOURS.start, "destination", COLOURS.destination, COLOURS.refuge],
          "line-width": 2,
        },
      });
      const routeLayer = (kind: string, paint: maplibregl.LineLayerSpecification["paint"]) =>
        m.addLayer({
          id: `route-${kind}`,
          type: "line",
          source: "routes",
          filter: ["==", ["get", "kind"], kind],
          layout: { "line-cap": "round", "line-join": "round" },
          paint,
        });
      routeLayer("refuge", { "line-color": COLOURS.refuge, "line-width": 6, "line-opacity": 0.9 });
      routeLayer("shortest", { "line-color": COLOURS.shortest, "line-width": 4, "line-dasharray": [2, 1.5], "line-opacity": 0.9 });
      routeLayer("safe_shortest", { "line-color": COLOURS.safe_shortest, "line-width": 5, "line-dasharray": [0.1, 1.6], "line-opacity": 0.95 });
      routeLayer("downgrade", { "line-color": COLOURS.downgrade, "line-width": 5, "line-dasharray": [2, 1.2], "line-opacity": 0.95 });
      routeLayer("recommended", { "line-color": COLOURS.recommended, "line-width": 7, "line-opacity": 0.9 });
      routeLayer("leg", { "line-color": COLOURS.recommended, "line-width": 3, "line-dasharray": [1, 1.5] });
      m.addLayer({
        id: "place-doors",
        type: "circle",
        source: "places",
        filter: ["==", ["geometry-type"], "Point"],
        paint: {
          "circle-radius": 4,
          "circle-color": ["match", ["get", "role"], "start", COLOURS.start, COLOURS.destination],
          "circle-stroke-color": "#fff",
          "circle-stroke-width": 1.5,
        },
      });
      sync(m, latest.current, ALL_PARTS, fitted);
      setStyleVersion((v) => v + 1);
    };
    m.on("style.load", addLayers);
    const fallback = window.setTimeout(() => {
      if (!styleParsed) m.setStyle(FALLBACK_STYLE);
    }, BASEMAP_TIMEOUT_MS);
    m.on("click", (e: MapMouseEvent) => clickHandler.current(e.lngLat.lat, e.lngLat.lng));

    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 8 });
    for (const layer of ["water-ok", "water-over"]) {
      m.on("mousemove", layer, (e) => {
        const depth = e.features?.[0]?.properties?.depth_m;
        const info = popupInfo.current;
        if (!info.options) return;
        const d = typeof depth === "number" ? depth : null;
        const over = d === null || d > info.limit;
        const text =
          d === null
            ? "Depth unknown · treated as too deep"
            : `${cm(d)} · ${describeDepth(d, info.height, info.options)}${over ? " · over your limit" : ""}`;
        m.getCanvas().style.cursor = "crosshair";
        popup.setLngLat(e.lngLat).setText(text).addTo(m);
      });
      m.on("mouseleave", layer, () => {
        m.getCanvas().style.cursor = "";
        popup.remove();
      });
    }
    // Browsers may clear a WebGL canvas while the page is hidden or its container is resized;
    // redraw when it is shown again or changes size, so the map never stays blank.
    const redraw = () => {
      m.resize();
      if (!fitted.current) sync(m, latest.current, ["area"], fitted); // first time it has a size
      m.triggerRepaint();
    };
    const onVisibility = () => {
      if (document.visibilityState === "visible") redraw();
    };
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("focus", redraw);
    const resizes = new ResizeObserver(redraw);
    resizes.observe(container.current);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("focus", redraw);
      resizes.disconnect();
      window.clearTimeout(fallback);
      window.clearTimeout(rebuildTimer);
      document.removeEventListener("visibilitychange", rebuild);
      try {
        m.remove();
      } catch {
        // removing a map whose context is already lost can throw; the new map does not need it
      }
      map.current = null;
    };
  }, [generation]);

  useEffect(() => {
    if (styleVersion && map.current) sync(map.current, props, ["area"], fitted);
  }, [styleVersion, props.area]);

  useEffect(() => {
    if (styleVersion && map.current) sync(map.current, props, ["network"], fitted);
  }, [styleVersion, props.network]);

  useEffect(() => {
    if (styleVersion && map.current) sync(map.current, props, ["water"], fitted);
  }, [styleVersion, props.water]);

  useEffect(() => {
    if (styleVersion && map.current) sync(map.current, props, ["limit"], fitted);
  }, [styleVersion, props.depthLimitM]);

  useEffect(() => {
    if (styleVersion && map.current) sync(map.current, props, ["trip"], fitted);
  }, [styleVersion, props.trip]);

  // Start and destination markers sit on the door actually used once a route exists.
  useEffect(() => {
    const m = map.current;
    if (!styleVersion || !m) return;
    const recommended = props.trip?.routes?.options.find((o) => o.kind === "recommended")?.route ?? null;
    const anyRoute = recommended ?? props.trip?.routes?.options.find((o) => o.route)?.route ?? null;
    for (const kind of ["start", "destination"] as const) {
      const chosen = kind === "start" ? props.start : props.destination;
      const end = anyRoute ? (kind === "start" ? anyRoute.from : anyRoute.to) : null;
      const at = end ?? chosen;
      if (!at) {
        markers.current[kind]?.remove();
        markers.current[kind] = undefined;
        continue;
      }
      if (!markers.current[kind]) {
        markers.current[kind] = new maplibregl.Marker({ element: markerElement(kind), anchor: "bottom" });
      }
      markers.current[kind]!.setLngLat([at.lon, at.lat]).addTo(m);
    }
  }, [styleVersion, props.start, props.destination, props.trip]);

  // Bring a newly planned trip into view.
  const lastFit = useRef<string>("");
  useEffect(() => {
    const m = map.current;
    if (!styleVersion || !m || !props.start || !props.destination) return;
    const key = `${props.start.lat},${props.start.lon},${props.destination.lat},${props.destination.lon}`;
    if (key === lastFit.current) return;
    lastFit.current = key;
    const lons = [props.start.lon, props.destination.lon];
    const lats = [props.start.lat, props.destination.lat];
    m.fitBounds(
      [
        [Math.min(...lons), Math.min(...lats)],
        [Math.max(...lons), Math.max(...lats)],
      ],
      { padding: 80, maxZoom: 17, duration: 600 },
    );
  }, [styleVersion, props.start, props.destination]);

  return (
    <>
      <div ref={container} className="map" role="application" aria-label="Map of Southbank" />
      {failed && (
        <div className="map-failed" role="alert">
          <p>
            <strong>The map stopped drawing.</strong> The browser ran out of graphics resources.
          </p>
          <button
            type="button"
            className="button"
            onClick={() => {
              setFailed(false);
              lastRebuild.current = Date.now();
              setGeneration((g) => g + 1);
            }}
          >
            Reload map
          </button>
          <p className="muted small">If this keeps happening, quit and reopen the browser.</p>
        </div>
      )}
    </>
  );
}
