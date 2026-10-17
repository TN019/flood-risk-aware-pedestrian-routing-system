// What the traveller should do next, worked out from a trip plan. Kept free of React so it can be
// tested on its own.

import { cm, distance } from "./format";
import type { RouteKind } from "./routeStyles";
import type { RouteJson, TripPlan } from "./types";

export type Situation =
  | "go" // a route fits the limit and it is the plain shortest way
  | "detour" // a route fits the limit, but it is not the plain shortest way
  | "choose" // no route fits: accept deeper water, or wait (at a shelter or where they are)
  | "downgrade" // no route fits, no shelter: accepting deeper water is the way forward
  | "shelter" // no route fits: go to a shelter and wait
  | "stay" // no route fits and they are already inside: stay there
  | "help" // no route, no shelter: emergency help
  | "unreachable"; // the places are not connected at all

export function route(trip: TripPlan, kind: RouteKind): RouteJson | null {
  switch (kind) {
    case "downgrade":
      return trip.downgrade?.route ?? null;
    case "refuge":
      return trip.refuge?.route ?? null;
    case "least_water":
      return trip.least_water?.route ?? null;
    default:
      return trip.routes?.options.find((o) => o.kind === kind)?.route ?? null;
  }
}

export function sameLine(a: RouteJson | null, b: RouteJson | null): boolean {
  return !!a && !!b && JSON.stringify(a.geometry) === JSON.stringify(b.geometry);
}

export function situation(trip: TripPlan): Situation {
  if (!trip.routes) return "unreachable";
  if (trip.has_safe_route) return sameLine(route(trip, "recommended"), route(trip, "shortest")) ? "go" : "detour";
  if (trip.downgrade && (trip.refuge || trip.origin.sheltered)) return "choose";
  if (trip.downgrade) return "downgrade";
  if (trip.origin.sheltered) return "stay";
  if (trip.refuge) return "shelter";
  return "help";
}

/** The route highlighted when a plan first appears; null shows the alternatives equally. */
export function defaultChoice(trip: TripPlan): RouteKind | null {
  switch (situation(trip)) {
    case "go":
    case "detour":
      return "recommended";
    case "downgrade":
      return "downgrade";
    case "shelter":
      return "refuge";
    case "stay":
    case "help":
      return trip.least_water ? "least_water" : null;
    default:
      return null;
  }
}

/** Why no route fits the traveller's limit, from the least water any route has to face. */
export function whyNoRoute(trip: TripPlan): string | null {
  const least = trip.least_water;
  if (!least) return null;
  const where = trip.destination.method === "point" ? "there" : `to ${trip.destination.label}`;
  if (least.required_depth_m === null) return `Every way ${where} crosses water of unknown depth.`;
  const depth = `${cm(least.required_depth_m)} of water (${least.required_label})`;
  const t = trip.traveller;
  const cap =
    t.mobility_aid === "none"
      ? `more than the ${cm(t.hard_limit_m)} anyone is routed through`
      : `more than the ${cm(t.hard_limit_m)} a ${t.mobility_aid_label} is routed through`;
  const limit = least.beyond_hard_limit ? cap : `deeper than your limit of ${cm(t.depth_limit_m)}`;
  return `Every way ${where} crosses at least ${depth}, ${limit}. The deepest point is marked on the map.`;
}

/** What the recommended route gains over the plain shortest way, when they differ. */
export function detourText(trip: TripPlan): string | null {
  const rec = route(trip, "recommended");
  const short = route(trip, "shortest");
  if (!rec || !short || sameLine(rec, short)) return null;
  const extra = Math.max(0, rec.metrics.length_m - short.metrics.length_m);
  const s = short.metrics;
  if (s.segments_over_limit > 0) {
    const crosses =
      s.max_depth_m === null
        ? "crosses water of unknown depth"
        : `crosses water deeper than your limit, up to ${cm(s.max_depth_m)} (${s.max_depth_label})`;
    return `The shortest way (${distance(s.length_m)}) ${crosses}. This route walks ${distance(extra)} further to stay within it.`;
  }
  const avoided = Math.max(0, s.wading_length_m - rec.metrics.wading_length_m);
  return `This route walks ${distance(extra)} further than the shortest way to avoid ${distance(avoided)} of water up to ${cm(s.max_depth_m ?? 0)} (${s.max_depth_label}).`;
}

/** The water a higher limit accepts, in words: "water up to the knee", "water below a 4-inch castor
 * axle", "a shallow puddle". */
export function acceptText(d: NonNullable<TripPlan["downgrade"]>): string {
  if (d.body_part !== null) return `water up to the ${d.label}`;
  return d.label.startsWith("a ") ? d.label : `water ${d.label}`;
}
