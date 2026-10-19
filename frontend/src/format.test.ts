import { describe, expect, it } from "vitest";
import { accessNote, cm, contains, describeDepth, distance, gradientPercent, gradientSummary, groupRoutes, hasGradients } from "./format";
import type { RouteOption } from "./types";

const options = {
  dry_depth_m: 0.02,
  landmarks: [
    { fraction: 0.039, name: "ankle" },
    { fraction: 0.285, name: "knee" },
  ],
};

describe("describeDepth", () => {
  it("matches the backend wording", () => {
    expect(describeDepth(null, 1.7, options)).toBe("unknown depth");
    expect(describeDepth(0.02, 1.7, options)).toBe("dry");
    expect(describeDepth(0.06, 1.7, options)).toBe("up to the ankle");
    expect(describeDepth(0.3, 1.7, options)).toBe("up to the knee");
    expect(describeDepth(1.2, 1.7, options)).toBe("above the shoulders");
  });

  it("depends on height", () => {
    expect(describeDepth(0.06, 1.2, options)).toBe("up to the knee");
  });
});

describe("contains", () => {
  const square: GeoJSON.Polygon = {
    type: "Polygon",
    coordinates: [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]], [[0.5, 0.5], [1, 0.5], [1, 1], [0.5, 1], [0.5, 0.5]]],
  };
  it("respects holes", () => {
    expect(contains(square, 1.5, 1.5)).toBe(true);
    expect(contains(square, 0.75, 0.75)).toBe(false);
    expect(contains(square, 3, 1)).toBe(false);
  });
});

describe("groupRoutes", () => {
  const line = (x: number): RouteOption["route"] => ({
    geometry: { type: "LineString", coordinates: [[0, 0], [x, 0]] },
    access_legs: [],
    uses_steps: false,
    max_gradient: null,
    min_gradient: null,
    from: { lat: 0, lon: 0, label: "" },
    to: { lat: 0, lon: 0, label: null },
    metrics: { length_m: x, travel_time_s: 1, max_depth_m: 0, max_depth_label: "dry", wading_length_m: 0, segments_over_limit: 0, detour_ratio: 0 },
  });
  it("draws identical routes once", () => {
    const groups = groupRoutes([
      { kind: "shortest", name: "", found: true, error: null, route: line(1) },
      { kind: "safe_shortest", name: "", found: true, error: null, route: line(2) },
      { kind: "recommended", name: "", found: true, error: null, route: line(2) },
    ]);
    expect(groups.map((g) => g.kinds)).toEqual([["shortest"], ["safe_shortest", "recommended"]]);
  });
});

describe("distance", () => {
  it("switches to km", () => {
    expect(distance(950)).toBe("950 m");
    expect(distance(1530)).toBe("1.5 km");
  });
});

describe("cm", () => {
  it("keeps a decimal only where it matters", () => {
    expect(cm(0.025)).toBe("2.5 cm");
    expect(cm(0.075)).toBe("7.5 cm");
    expect(cm(0.0663)).toBe("6.6 cm");
    expect(cm(0.05)).toBe("5 cm");
    expect(cm(0.4845)).toBe("48 cm");
  });
});

describe("accessNote", () => {
  const routes = { step_free: true, steps_avoided: false, steep_avoided: false };
  it("says nothing for walkers", () => {
    expect(accessNote({ ...routes, step_free: false })).toBe("");
  });
  it("names what the routes avoid", () => {
    expect(accessNote(routes)).toBe("Every route is step-free.");
    expect(accessNote({ ...routes, steps_avoided: true })).toBe("Every route avoids the steps on the shortest way.");
    expect(accessNote({ ...routes, steep_avoided: true })).toBe("Every route avoids the paths steeper than 1:14 on the shortest way.");
    expect(accessNote({ ...routes, steps_avoided: true, steep_avoided: true })).toBe(
      "Every route avoids the steps and the paths steeper than 1:14 on the shortest way.",
    );
  });
});

describe("gradients", () => {
  it("shows plain percentages, without a sign", () => {
    expect(gradientPercent(0.0829)).toBe("8.3%");
    expect(gradientPercent(-0.024)).toBe("2.4%");
    expect(gradientPercent(0)).toBe("0.0%");
    expect(gradientSummary({ max_gradient: 0.024, min_gradient: 0.006 })).toBe("Gradient 0.6% to 2.4%");
    expect(gradientSummary({ max_gradient: 0.024, min_gradient: 0.024 })).toBe("Gradient 2.4%");
  });
  it("never shows NaN when a gradient is missing", () => {
    for (const g of [null, undefined, Number.NaN, Infinity]) expect(gradientPercent(g)).toBe("—");
    expect(hasGradients({ max_gradient: null, min_gradient: null })).toBe(false);
    expect(gradientSummary({ max_gradient: null, min_gradient: null })).toBe("No gradient data");
    expect(gradientSummary({ max_gradient: 0.03 })).toBe("No gradient data"); // an API without min_gradient
    expect(gradientSummary({})).toBe("No gradient data");
    expect(gradientSummary({ max_gradient: Number.NaN, min_gradient: 0.01 })).toBe("No gradient data");
  });
});
