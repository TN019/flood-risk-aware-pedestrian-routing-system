import { describe, expect, it } from "vitest";
import { defaultChoice, detourText, situation, whyNoRoute } from "./guidance";
import { english as t } from "./i18n/translate";
import type { RouteJson, RouteOption, TripPlan } from "./types";

function line(x: number, metrics: Partial<RouteJson["metrics"]> = {}): RouteJson {
  return {
    geometry: { type: "LineString", coordinates: [[0, 0], [x, 0]] },
    access_legs: [],
    uses_steps: false,
    max_gradient: null,
    min_gradient: null,
    from: { lat: 0, lon: 0, label: "" },
    to: { lat: 0, lon: 0, label: null },
    metrics: {
      length_m: x,
      travel_time_s: x,
      max_depth_m: 0,
      max_depth_label: "dry",
      wading_length_m: 0,
      segments_over_limit: 0,
      detour_ratio: 0,
      ...metrics,
    },
  };
}

function option(kind: RouteOption["kind"], r: RouteJson | null): RouteOption {
  return { kind, name: kind, found: !!r, error: r ? null : "No route keeps you within your limit (7 cm).", route: r };
}

function plan(p: Partial<TripPlan> & { shortest?: RouteJson; recommended?: RouteJson | null }): TripPlan {
  const shortest = p.shortest ?? line(300);
  const recommended = p.recommended === undefined ? shortest : p.recommended;
  return {
    start: { label: "Start", method: "point", point: { lat: 0, lon: 0 }, building: null, access: [] },
    destination: { label: "Crown", method: "entrances", point: { lat: 0, lon: 0 }, building: null, access: [] },
    traveller: {
      depth_limit_m: 0.0663,
      limit_label: "up to the ankle",
      height_m: 1.7,
      hard_limit_m: 0.5,
      mobility_aid: "none",
      mobility_aid_label: "none",
    },
    origin: { level: "ok", level_rank: 0, depth_m: 0, depth_label: "dry", sheltered: false, above_knee: false },
    has_safe_route: recommended !== null,
    routes: {
      alpha: 2,
      blocked_edges: 0,
      step_free: false,
      steps_avoided: false,
      steep_avoided: false,
      options: [option("shortest", shortest), option("safe_shortest", recommended), option("recommended", recommended)],
    },
    downgrade: null,
    refuge: null,
    emergency: null,
    least_water: null,
    ...p,
  };
}

const least = (depth: number | null, beyond = false): TripPlan["least_water"] => ({
  required_depth_m: depth,
  required_label: "up to the mid calf",
  beyond_hard_limit: beyond,
  deepest_point: { lat: 0, lon: 0 },
  route: line(400),
});
const refuge: TripPlan["refuge"] = { name: "Shelter", entrance_label: "entrance", within_limit: true, building: { type: "Point", coordinates: [0, 0] }, route: line(35) };
const downgrade: NonNullable<TripPlan["downgrade"]> = {
  body_part: "knee",
  aid_level: null,
  label: "knee",
  body_part_label: "knee",
  water: "water up to the knee",
  depth_limit_m: 0.48,
  required_depth_m: 0.4,
  route: line(300),
};

describe("situation", () => {
  it("goes straight when the shortest way fits", () => {
    const p = plan({});
    expect(situation(p)).toBe("go");
    expect(defaultChoice(p)).toBe("recommended");
  });

  it("explains a detour", () => {
    const p = plan({ shortest: line(300, { max_depth_m: 0.19, max_depth_label: "up to the lower calf", wading_length_m: 36, segments_over_limit: 2 }), recommended: line(385) });
    expect(situation(p)).toBe("detour");
    expect(detourText(p, t)).toBe(
      "The shortest way (300 m) crosses water deeper than your limit, up to 19 cm (up to the lower calf). This route walks 85 m further to stay within it.",
    );
  });

  it("says when the shortest way's water is of unknown depth", () => {
    const p = plan({ shortest: line(300, { max_depth_m: null, max_depth_label: "unknown depth", segments_over_limit: 1 }), recommended: line(312) });
    expect(detourText(p, t)).toBe("The shortest way (300 m) crosses water of unknown depth. This route walks 12 m further to stay within it.");
  });

  it("offers a choice when a higher limit or a shelter would both work", () => {
    const p = plan({ recommended: null, downgrade, refuge, least_water: least(0.4) });
    expect(situation(p)).toBe("choose");
    expect(defaultChoice(p)).toBeNull();
  });

  it("offers staying inside against a higher limit for someone indoors", () => {
    const origin = { level: "ok" as const, level_rank: 0, depth_m: null, depth_label: "indoors", sheltered: true, above_knee: false };
    expect(situation(plan({ recommended: null, downgrade, origin, least_water: least(0.4) }))).toBe("choose");
    const stay = plan({ recommended: null, origin, least_water: least(0.55, true) });
    expect(situation(stay)).toBe("stay");
    expect(defaultChoice(stay)).toBe("least_water");
  });

  it("sends to a shelter, or to emergency help when there is none", () => {
    expect(situation(plan({ recommended: null, refuge, least_water: least(0.55, true) }))).toBe("shelter");
    expect(situation(plan({ recommended: null, least_water: least(0.55, true) }))).toBe("help");
    expect(situation(plan({ routes: null }))).toBe("unreachable");
  });
});

describe("whyNoRoute", () => {
  it("names the least water and the limit it breaks", () => {
    expect(whyNoRoute(plan({ recommended: null, least_water: least(0.32) }), t)).toBe(
      "Every way to Crown crosses at least 32 cm of water (up to the mid calf), deeper than your limit of 6.6 cm. The deepest point is marked on the map.",
    );
    expect(whyNoRoute(plan({ recommended: null, least_water: least(0.55, true) }), t)).toContain(
      "more than the 50 cm anyone is routed through",
    );
    expect(whyNoRoute(plan({ recommended: null, least_water: least(null, true) }), t)).toBe("Every way to Crown crosses water of unknown depth.");
  });
});

describe("mobility aids", () => {
  it("names the device's cap when the least water is beyond it", () => {
    const p = plan({ recommended: null, least_water: least(0.04, true) });
    p.traveller = { ...p.traveller, depth_limit_m: 0.02, hard_limit_m: 0.025, mobility_aid: "mobility_scooter", mobility_aid_label: "mobility scooter" };
    expect(whyNoRoute(p, t)).toContain("more than the 2.5 cm a mobility scooter is routed through");
  });

  it("says where to when the destination is a building, and not for a point", () => {
    const p = plan({ recommended: null, least_water: least(0.32) });
    p.destination = { ...p.destination, method: "point" };
    expect(whyNoRoute(p, t)).toMatch(/^Every way there crosses at least 32 cm/);
  });
});
