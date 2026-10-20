// What the traveller should do next, worked out from a trip plan. Kept free of React so it can be
// tested on its own; the sentences come from the catalogue of the chosen language (i18n/messages).

import { cm, distance } from "./format";
import type { Translate } from "./i18n/translate";
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
export function whyNoRoute(trip: TripPlan, t: Translate): string | null {
  const least = trip.least_water;
  if (!least) return null;
  const to = trip.destination.method === "point" ? "" : "To";
  const place = trip.destination.label;
  if (least.required_depth_m === null) return t(`why.unknown${to}`, { place });
  const tr = trip.traveller;
  const values = { place, depth: cm(least.required_depth_m), label: least.required_label, aid: tr.mobility_aid_label };
  if (!least.beyond_hard_limit) return t(`why.overLimit${to}`, { ...values, limit: cm(tr.depth_limit_m) });
  const cap = tr.mobility_aid === "none" ? "overCap" : "overAidCap";
  return t(`why.${cap}${to}`, { ...values, limit: cm(tr.hard_limit_m) });
}

/** What the recommended route gains over the plain shortest way, when they differ. */
export function detourText(trip: TripPlan, t: Translate): string | null {
  const rec = route(trip, "recommended");
  const short = route(trip, "shortest");
  if (!rec || !short || sameLine(rec, short)) return null;
  const extra = distance(Math.max(0, rec.metrics.length_m - short.metrics.length_m));
  const s = short.metrics;
  if (s.segments_over_limit > 0) {
    if (s.max_depth_m === null) return t("detour.unknown", { distance: distance(s.length_m), extra });
    return t("detour.overLimit", { distance: distance(s.length_m), depth: cm(s.max_depth_m), label: s.max_depth_label, extra });
  }
  const avoided = Math.max(0, s.wading_length_m - rec.metrics.wading_length_m);
  return t("detour.avoid", { extra, water: distance(avoided), depth: cm(s.max_depth_m ?? 0), label: s.max_depth_label });
}
