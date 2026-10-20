import type { Translate } from "./i18n/translate";
import type { Geometry, Options, RouteJson, RouteOption, TripPlan } from "./types";

// Numbers are written the same way in every language: Western digits, a full stop as the decimal
// point, and the unit symbols cm, m and km (docs/languages.md).

/** Where water of this depth reaches on a person of this height, e.g. "up to the ankle", in the
 * words the API sent. Mirrors floodroute.risk.profile.depth_reach. */
export function describeDepth(
  depthM: number | null,
  heightM: number,
  options: Pick<Options, "landmarks" | "depth_labels" | "dry_depth_m">,
): string {
  if (depthM === null) return options.depth_labels.unknown;
  if (depthM <= options.dry_depth_m) return options.depth_labels.dry;
  for (const { fraction, label } of options.landmarks) {
    if (depthM <= fraction * heightM) return label;
  }
  return options.depth_labels.above;
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

export function minutes(seconds: number, t: Translate): string {
  return t("unit.min", { count: Math.max(1, Math.round(seconds / 60)) });
}

export function depthSummary(depthM: number | null, label: string, dryDepthM: number, t: Translate): string {
  if (depthM === null) return t("depth.unknown");
  if (depthM <= dryDepthM) return t("depth.none");
  return t("depth.withLabel", { depth: cm(depthM), label });
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
export function accessNote(
  routes: Pick<NonNullable<TripPlan["routes"]>, "step_free" | "steps_avoided" | "steep_avoided">,
  t: Translate,
): string {
  if (routes.steps_avoided && routes.steep_avoided) return t("access.avoidsBoth");
  if (routes.steps_avoided) return t("access.avoidsSteps");
  if (routes.steep_avoided) return t("access.avoidsSteep");
  return routes.step_free ? t("access.stepFree") : "";
}

/** A measured gradient (rise over run) as a plain percentage, e.g. "8.3%"; "—" when it is missing. */
export function gradientPercent(g: number | null | undefined): string {
  return typeof g === "number" && Number.isFinite(g) ? `${(Math.abs(g) * 100).toFixed(1)}%` : "—";
}

/** Whether a route has a steepest and a gentlest measured gradient to show. */
export function hasGradients(route: Partial<Pick<RouteJson, "max_gradient" | "min_gradient">>): boolean {
  return [route.max_gradient, route.min_gradient].every((g) => typeof g === "number" && Number.isFinite(g));
}

/** The measured gradients along a route, e.g. "Gradient 0.6% to 2.4%". */
export function gradientSummary(route: Partial<Pick<RouteJson, "max_gradient" | "min_gradient">>, t: Translate): string {
  if (!hasGradients(route)) return t("gradient.none");
  const gentlest = gradientPercent(route.min_gradient);
  const steepest = gradientPercent(route.max_gradient);
  return gentlest === steepest ? t("gradient.one", { gradient: steepest }) : t("gradient.range", { from: gentlest, to: steepest });
}
