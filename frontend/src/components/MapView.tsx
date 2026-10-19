import maplibregl, { type GeoJSONSource, type LngLatBoundsLike, type MapMouseEvent, type PaddingOptions } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { cm, describeDepth } from "../format";
import { route as routeOf } from "../guidance";
import { DRAW_ORDER, ROUTE_STYLES, type RouteKind } from "../routeStyles";
import type { Area, ChosenPoint, FeatureCollection, Options, TripPlan } from "../types";

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
  refuge: ROUTE_STYLES.refuge.colour,
  deepest: "#b2182b",
  start: "#1a9850",
  destination: "#d73027",
};

const EMPTY: FeatureCollection = { type: "FeatureCollection", features: [] };

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
  selected: RouteKind | null; // highlighted; the others are dimmed
  focus: number; // bumped when the traveller picks a route: bring it into view
  onMapClick: (lat: number, lon: number) => void;
}

/** Every route of the plan, drawn once per distinct line. Where several follow the same line, it is
 * drawn as the selected one, or else as the most important (latest in DRAW_ORDER). */
function routeFeatures(trip: TripPlan | null, selected: RouteKind | null): FeatureCollection {
  if (!trip) return EMPTY;
  const groups: { kinds: RouteKind[]; geometry: GeoJSON.Geometry; key: string }[] = [];
  for (const kind of DRAW_ORDER) {
    const r = routeOf(trip, kind);
    if (!r) continue;
    const key = JSON.stringify(r.geometry);
    const group = groups.find((g) => g.key === key);
    if (group) group.kinds.push(kind);
    else groups.push({ kinds: [kind], geometry: r.geometry, key });
  }
  const features: GeoJSON.Feature[] = groups.map((g) => {
    const isSelected = selected !== null && g.kinds.includes(selected);
    const kind = isSelected ? selected : g.kinds[g.kinds.length - 1];
    return { type: "Feature", properties: { kind, selected: isSelected, dim: selected !== null && !isSelected }, geometry: g.geometry };
  });
  // Selected (or else recommended) route last, so it is drawn above the others in its layer.
  features.sort((a, b) => Number(a.properties!.selected) - Number(b.properties!.selected));
  const legsOf = routeOf(trip, selected ?? "recommended");
  for (const leg of legsOf?.access_legs ?? []) {
    features.push({ type: "Feature", properties: { kind: "leg", selected: true, dim: false }, geometry: leg });
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
  const least = trip.least_water;
  if (least) {
    const depth = least.required_depth_m === null ? "unknown depth" : `${cm(least.required_depth_m)} (${least.required_label})`;
    features.push({
      type: "Feature",
      properties: { role: "deepest", label: `Deepest point on the least-water route: ${depth}` },
      geometry: { type: "Point", coordinates: [least.deepest_point.lon, least.deepest_point.lat] },
    });
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
        source("routes")?.setData(routeFeatures(p.trip, p.selected));
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

/** Room around a fitted trip or route: on a desktop the legend takes the bottom left; on a phone
 * Get help, the legend and the click hint take the top. */
function fitPadding(): PaddingOptions {
  return window.matchMedia("(max-width: 760px)").matches
    ? { top: 90, right: 40, bottom: 40, left: 40 }
    : { top: 70, right: 60, bottom: 170, left: 60 };
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
    // For scripts/capture.mjs, which records the README images: development builds only.
    if (import.meta.env.DEV) (window as unknown as { __floodrouteMap?: maplibregl.Map }).__floodrouteMap = m;
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
      const lineLayout: maplibregl.LineLayerSpecification["layout"] = { "line-cap": "round", "line-join": "round" };
      const isRoute: maplibregl.FilterSpecification = ["!=", ["get", "kind"], "leg"];
      // A white outline keeps every route readable above the water lines.
      m.addLayer({
        id: "route-casing",
        type: "line",
        source: "routes",
        filter: isRoute,
        layout: lineLayout,
        paint: { "line-color": "#fff", "line-width": 11, "line-opacity": ["case", ["get", "dim"], 0.35, 0.85] },
      });
      for (const kind of DRAW_ORDER) {
        const style = ROUTE_STYLES[kind];
        m.addLayer({
          id: `route-${kind}`,
          type: "line",
          source: "routes",
          filter: ["==", ["get", "kind"], kind],
          layout: lineLayout,
          paint: {
            "line-color": style.colour,
            "line-width": style.map.width,
            "line-opacity": ["case", ["get", "dim"], 0.3, 0.95],
            ...(style.map.dash ? { "line-dasharray": style.map.dash } : {}),
          },
        });
      }
      // The selected route again, solid and on top of everything else.
      const colourByKind: maplibregl.ExpressionSpecification = [
        "match",
        ["get", "kind"],
        ...DRAW_ORDER.flatMap((k) => [k, ROUTE_STYLES[k].colour]),
        ROUTE_STYLES.recommended.colour,
      ] as unknown as maplibregl.ExpressionSpecification;
      const selectedRoute: maplibregl.FilterSpecification = ["all", ["==", ["get", "selected"], true], isRoute];
      m.addLayer({ id: "route-selected-casing", type: "line", source: "routes", filter: selectedRoute, layout: lineLayout, paint: { "line-color": "#fff", "line-width": 13 } });
      m.addLayer({ id: "route-selected", type: "line", source: "routes", filter: selectedRoute, layout: lineLayout, paint: { "line-color": colourByKind, "line-width": 8 } });
      m.addLayer({
        id: "route-leg",
        type: "line",
        source: "routes",
        filter: ["==", ["get", "kind"], "leg"],
        layout: lineLayout,
        paint: { "line-color": "#333", "line-width": 3, "line-dasharray": [1, 1.5] },
      });
      m.addLayer({
        id: "place-doors",
        type: "circle",
        source: "places",
        filter: ["all", ["==", ["geometry-type"], "Point"], ["!=", ["get", "role"], "deepest"]],
        paint: {
          "circle-radius": 4,
          "circle-color": ["match", ["get", "role"], "start", COLOURS.start, COLOURS.destination],
          "circle-stroke-color": "#fff",
          "circle-stroke-width": 1.5,
        },
      });
      m.addLayer({
        id: "deepest-point",
        type: "circle",
        source: "places",
        filter: ["==", ["get", "role"], "deepest"],
        paint: { "circle-radius": 8, "circle-color": COLOURS.deepest, "circle-stroke-color": "#fff", "circle-stroke-width": 3 },
      });
      sync(m, latest.current, ALL_PARTS, fitted);
      setStyleVersion((v) => v + 1);
    };
    m.on("style.load", addLayers);
    const fallback = window.setTimeout(() => {
      if (!styleParsed) m.setStyle(FALLBACK_STYLE);
    }, BASEMAP_TIMEOUT_MS);
    m.on("click", (e: MapMouseEvent) => clickHandler.current(e.lngLat.lat, e.lngLat.lng));

    // The hover popup must not catch clicks: it sits next to the pointer, and a click on it would
    // not reach the map (so a start or destination on a flooded street could not be set).
    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 8, className: "hover-popup" });
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
    m.on("mousemove", "deepest-point", (e) => {
      const label = e.features?.[0]?.properties?.label;
      if (typeof label === "string") popup.setLngLat(e.lngLat).setText(label).addTo(m);
    });
    m.on("mouseleave", "deepest-point", () => popup.remove());
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
  }, [styleVersion, props.trip, props.selected]);

  // Bring the route the traveller picked into view.
  useEffect(() => {
    const m = map.current;
    const r = props.trip && props.selected ? routeOf(props.trip, props.selected) : null;
    if (!props.focus || !m || !r || r.geometry.type !== "LineString") return;
    const coords = r.geometry.coordinates;
    const lons = coords.map((c) => c[0]);
    const lats = coords.map((c) => c[1]);
    m.fitBounds(
      [
        [Math.min(...lons), Math.min(...lats)],
        [Math.max(...lons), Math.max(...lats)],
      ],
      { padding: fitPadding(), maxZoom: 17, duration: 500 },
    );
  }, [props.focus]);

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
      { padding: fitPadding(), maxZoom: 17, duration: 600 },
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
