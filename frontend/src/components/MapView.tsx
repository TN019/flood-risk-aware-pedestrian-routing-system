import maplibregl, { type GeoJSONSource, type LngLatBoundsLike, type MapMouseEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { cm, describeDepth, groupRoutes } from "../format";
import type { Area, ChosenPoint, FeatureCollection, Options, RouteJson, TripPlan } from "../types";

// Free vector basemap built from OpenStreetMap data (no key needed).
const BASEMAP = "https://tiles.openfreemap.org/styles/positron";

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
  const [ready, setReady] = useState(false);
  clickHandler.current = props.onMapClick;
  popupInfo.current = { limit: props.depthLimitM, height: props.heightM, options: props.options };

  useEffect(() => {
    if (!container.current) return;
    const m = new maplibregl.Map({
      container: container.current,
      style: BASEMAP,
      center: [144.962, -37.826],
      zoom: 14.5,
      maxZoom: 19,
      attributionControl: { compact: true },
    });
    map.current = m;
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.on("load", () => {
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
      m.on("click", (e: MapMouseEvent) => clickHandler.current(e.lngLat.lat, e.lngLat.lng));
      setReady(true);
    });
    return () => {
      m.remove();
      map.current = null;
    };
  }, []);

  const source = (id: string) => map.current?.getSource(id) as GeoJSONSource | undefined;

  useEffect(() => {
    if (!ready || !props.area) return;
    const wrap = (g: GeoJSON.Geometry): FeatureCollection => ({ type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: g }] });
    source("area")?.setData(wrap(props.area.study_area));
    source("ring")?.setData(wrap(props.area.routable_area));
    const [w, s, e, n] = props.area.bounds;
    map.current?.fitBounds([[w, s], [e, n]] as LngLatBoundsLike, { padding: 20, duration: 0 });
  }, [ready, props.area]);

  useEffect(() => {
    if (ready) source("network")?.setData(props.network ?? EMPTY);
  }, [ready, props.network]);

  useEffect(() => {
    if (ready) source("water")?.setData(props.water ?? EMPTY);
  }, [ready, props.water]);

  useEffect(() => {
    const m = map.current;
    if (!ready || !m) return;
    // Unknown depth (null or missing) counts as too deep.
    const depth: maplibregl.ExpressionSpecification = ["coalesce", ["get", "depth_m"], 99];
    m.setFilter("water-over", [">", depth, props.depthLimitM]);
    m.setFilter("water-ok", ["<=", depth, props.depthLimitM]);
  }, [ready, props.depthLimitM]);

  useEffect(() => {
    if (!ready) return;
    source("routes")?.setData(routeFeatures(props.trip));
    source("places")?.setData(placeFeatures(props.trip));
  }, [ready, props.trip]);

  // Start and destination markers sit on the door actually used once a route exists.
  useEffect(() => {
    const m = map.current;
    if (!ready || !m) return;
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
  }, [ready, props.start, props.destination, props.trip]);

  // Bring a newly planned trip into view.
  const lastFit = useRef<string>("");
  useEffect(() => {
    const m = map.current;
    if (!ready || !m || !props.start || !props.destination) return;
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
  }, [ready, props.start, props.destination]);

  return <div ref={container} className="map" role="application" aria-label="Map of Southbank" />;
}
