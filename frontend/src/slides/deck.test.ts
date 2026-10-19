import { describe, expect, it } from "vitest";
import walkthrough from "../../../docs/walkthrough.md?raw";
import { CLIPS, clipUrl } from "./content";
import { hashFor, keyMove, moveTo, slideFromHash, swipeMove } from "./deck";

describe("slideFromHash", () => {
  it("reads the slide number, from 1", () => {
    expect(slideFromHash("#1", 15)).toBe(0);
    expect(slideFromHash("#3", 15)).toBe(2);
    expect(slideFromHash(hashFor(14), 15)).toBe(14);
  });

  it("keeps within the deck", () => {
    expect(slideFromHash("#99", 15)).toBe(14);
    expect(slideFromHash("#15", 14)).toBe(13);
    expect(slideFromHash("#0", 15)).toBe(0);
    expect(slideFromHash("#-2", 15)).toBe(0);
  });

  it("starts at the first slide without a number", () => {
    expect(slideFromHash("", 15)).toBe(0);
    expect(slideFromHash("#", 15)).toBe(0);
    expect(slideFromHash("#intro", 15)).toBe(0);
    expect(slideFromHash("#2.5", 15)).toBe(0);
  });
});

describe("moveTo", () => {
  it("stops at either end", () => {
    expect(moveTo("next", 3, 15)).toBe(4);
    expect(moveTo("next", 14, 15)).toBe(14);
    expect(moveTo("previous", 0, 15)).toBe(0);
    expect(moveTo("first", 9, 15)).toBe(0);
    expect(moveTo("last", 2, 15)).toBe(14);
  });
});

describe("keyMove", () => {
  it("moves on arrows, Page Up and Down, Space, Home and End", () => {
    expect(keyMove("ArrowRight", false)).toBe("next");
    expect(keyMove("PageDown", false)).toBe("next");
    expect(keyMove(" ", false)).toBe("next");
    expect(keyMove(" ", true)).toBe("previous");
    expect(keyMove("ArrowLeft", false)).toBe("previous");
    expect(keyMove("PageUp", false)).toBe("previous");
    expect(keyMove("Home", false)).toBe("first");
    expect(keyMove("End", false)).toBe("last");
    expect(keyMove("a", false)).toBeNull();
  });
});

describe("swipeMove", () => {
  it("moves on a sideways swipe only", () => {
    expect(swipeMove(-80, 10)).toBe("next");
    expect(swipeMove(80, -10)).toBe("previous");
    expect(swipeMove(-20, 0)).toBeNull();
    expect(swipeMove(-60, 80)).toBeNull();
  });
});

describe("clips", () => {
  it("are the walkthrough's clips, in its order", () => {
    const names = [...walkthrough.matchAll(/images\/([\w-]+)\.gif/g)].map((m) => m[1]);
    expect(CLIPS.map((c) => c.name)).toEqual(names);
  });

  it("are all in docs/images", () => {
    for (const clip of CLIPS) expect(clipUrl(clip.name), clip.name).toBeTruthy();
  });
});
