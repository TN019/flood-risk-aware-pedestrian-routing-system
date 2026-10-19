import { describe, expect, it } from "vitest";
import { sharedLocation } from "./GetHelp";

describe("Get help", () => {
  it("says which location an SOS shares", () => {
    expect(sharedLocation(null)).toBe("no location (set a start to share one)");
    const point = { lat: -37.82, lon: 144.96, label: null, footprint: null };
    expect(sharedLocation({ ...point, source: "location" })).toBe("your current location");
    expect(sharedLocation({ ...point, source: "map" })).toBe("your start point as your location");
  });
});
