import type { Geometry, Options, RouteJson, RouteOption, TripPlan } from "./types";

/** Where water of this depth reaches on a person of this height, e.g. "up to the ankle".
 * Mirrors floodroute.risk.profile.describe_depth. */
export function describeDepth(depthM: number | null, heightM: number, options: Pick<Options, "landmarks" | "dry_depth_m">): string {
  if (depthM === null) return "unknown depth";
  if (depthM <= options.dry_depth_m) return "dry";
  for (const { fraction, name } of options.landmarks) {
    if (depthM <= fraction * heightM) return `up to the ${name}`;
  }
  return "above the shoulders";
}

/** Centimetres: whole above 10 cm; below that, one decimal when it matters (2.5 cm, 6.6 cm). */
export function cm(depthM: number): string {
  const value = depthM * 100;
  const whole = Math.round(value);
  if (value >= 10 || Math.abs(value - whole) < 0.05) return `${whole} cm`;
  return `${value.toFixed(1)} cm`;
}

export function distance(metres: number): string {
  return metres < 1000 ? `${Math.round(metres)} m` : `${(metres / 1000).toFixed(1)} km`;
}

export function minutes(seconds: number): string {
  const m = Math.max(1, Math.round(seconds / 60));
  return `${m} min`;
}

export function depthSummary(depthM: number | null, label: string, dryDepthM: number): string {
  if (depthM === null) return "unknown";
  if (depthM <= dryDepthM) return "none";
  return `${cm(depthM)} (${label})`;
}

/** Point-in-polygon for GeoJSON Polygon / MultiPolygon in lon/lat (even–odd rule). */
export function contains(geometry: Geometry, lon: number, lat: number): boolean {
  const polygons =
    geometry.type === "Polygon" ? [geometry.coordinates] : geometry.type === "MultiPolygon" ? geometry.coordinates : [];
  return polygons.some((rings) => {
    let inside = false;
    for (const ring of rings) {
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const [xi, yi] = ring[i];
        const [xj, yj] = ring[j];
        if (yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
      }
    }
    return inside;
  });
}

/** Routes that follow the same line are drawn once, styled as the most important of them. */
export function groupRoutes(options: RouteOption[]): { option: RouteOption; kinds: RouteOption["kind"][] }[] {
  const groups: { option: RouteOption; kinds: RouteOption["kind"][]; key: string }[] = [];
  for (const option of options) {
    if (!option.route) continue;
    const key = JSON.stringify(option.route.geometry);
    const match = groups.find((g) => g.key === key);
    if (match) match.kinds.push(option.kind);
    else groups.push({ option, kinds: [option.kind], key });
  }
  return groups.map(({ option, kinds }) => ({ option, kinds }));
}

/** What the routes leave out for a mobility aid user, as a sentence (empty for walkers). */
export function accessNote(routes: Pick<NonNullable<TripPlan["routes"]>, "step_free" | "steps_avoided" | "steep_avoided">): string {
  const avoided = [routes.steps_avoided && "the steps", routes.steep_avoided && "the paths steeper than 1:14"].filter(Boolean);
  if (avoided.length > 0) return `Every route avoids ${avoided.join(" and ")} on the shortest way.`;
  return routes.step_free ? "Every route is step-free." : "";
}

/** A gradient (rise over run) as a percentage, e.g. "8.3%". */
export function gradientPercent(g: number): string {
  return g <= 0 ? "0%" : `${(g * 100).toFixed(1)}%`;
}

/** A gradient as a "1 in N" ratio, e.g. "1 in 12.1", kept on one line. */
export function gradientRatio(g: number): string {
  if (g <= 0) return "flat";
  const run = 1 / g;
  return `1\u00a0in\u00a0${run >= 100 ? Math.round(run) : Number(run.toPrecision(3))}`;
}

/** A gradient as a percentage and a "1 in N" ratio, e.g. "8.3% (1 in 12.1)". */
export function gradient(g: number): string {
  return `${gradientPercent(g)} (${gradientRatio(g)})`;
}

/** A gradient limit as a ratio and a percentage, e.g. "1:14 (7.1%)". */
export function gradientLimit(g: number): string {
  return `1:${Math.round(1 / g)} (${(g * 100).toFixed(1)}%)`;
}

/** The steepest path the traveller may be routed on: only mobility aid users have one. */
export function travellerGradientLimit(trip: Pick<TripPlan, "traveller">, options: Pick<Options, "max_gradient">): number | null {
  return trip.traveller.mobility_aid === "none" ? null : options.max_gradient;
}

/** The steepest and gentlest measured gradient along a route, and the traveller's limit if they have one. */
export function gradientSummary(route: Pick<RouteJson, "max_gradient" | "min_gradient">, limit: number | null): string {
  const within = limit === null ? "" : ` · your limit ${gradientLimit(limit)}`;
  if (route.max_gradient === null || route.min_gradient === null) return `No gradient data${within}`;
  return `Steepest ${gradient(route.max_gradient)} · gentlest ${gradient(route.min_gradient)}${within}`;
}
