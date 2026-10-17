import type { Geometry, Options, RouteOption } from "./types";

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
