import { describe, expect, it } from "vitest";
import { contains, describeDepth, distance, groupRoutes } from "./format";
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
