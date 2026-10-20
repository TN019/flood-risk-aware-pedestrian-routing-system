import { describe, expect, it } from "vitest";
import { english as t } from "../i18n/translate";
import { sharedLocation } from "./GetHelp";
import { sharedText } from "./Sos";

describe("Get help", () => {
  it("says which location an SOS shares", () => {
    const shared = (start: Parameters<typeof sharedLocation>[0]) => sharedText(sharedLocation(start), t);
    expect(shared(null)).toBe("no location (set a start to share one)");
    const point = { lat: -37.82, lon: 144.96, label: null, footprint: null };
    expect(shared({ ...point, source: "location" })).toBe("your current location");
    expect(shared({ ...point, source: "map" })).toBe("your start point as your location");
  });

  it("adds the water depth where the trip plan says the traveller stands", () => {
    expect(sharedText({ place: "here", depth: null }, t)).toBe("your location");
    expect(sharedText({ place: "here", depth: "52 cm" }, t)).toBe("your location and 52 cm water depth");
  });
});
