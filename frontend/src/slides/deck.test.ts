import { describe, expect, it } from "vitest";
import walkthrough from "../../../docs/walkthrough.md?raw";
import { CLIPS, clipUrl, deckSlides, type DeckSlide, LANGUAGES, SHARE } from "./content";
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

describe("deck", () => {
  const clips = [...walkthrough.matchAll(/images\/([\w-]+)\.gif/g)].map((m) => m[1]);
  const names = (slides: DeckSlide[]) => slides.map((s) => (s.kind === "clip" ? s.clip.name : s.kind));
  const shown = (slides: DeckSlide[]) => slides.flatMap((s) => ("clip" in s ? [s.clip.name] : []));

  it("lists the walkthrough's clips, in its order", () => {
    expect(CLIPS.map((c) => c.name)).toEqual(clips);
  });

  it("shows every walkthrough clip, on a clip slide or the languages slide", () => {
    expect(shown(deckSlides(false))).toEqual([...clips.filter((c) => c !== LANGUAGES.clip), LANGUAGES.clip]);
  });

  it("is the title, the clips but the languages one in order, then languages, testing and sources", () => {
    expect(names(deckSlides(false))).toEqual(["intro", ...clips.filter((c) => c !== "languages"), "languages", "testing", "reference"]);
  });

  it("ends with the QR codes at a public address", () => {
    expect(names(deckSlides(true))).toEqual(["intro", ...clips.filter((c) => c !== "languages"), "languages", "testing", "reference", "share"]);
  });

  it("has 17 slides, and 18 at a public address", () => {
    expect(deckSlides(false)).toHaveLength(17);
    expect(deckSlides(true)).toHaveLength(18);
  });

  it("goes to the last slide from the QR codes' address when opened locally", () => {
    expect(slideFromHash("#18", deckSlides(false).length)).toBe(16);
    expect(slideFromHash("#18", deckSlides(true).length)).toBe(17);
  });

  it("has the app's QR code in the middle", () => {
    expect(SHARE.pages.map((p) => p.path)).toEqual(["/reference/", "/", "/benchmark/"]);
  });

  it("has every clip in docs/images", () => {
    for (const clip of CLIPS) expect(clipUrl(clip.name), clip.name).toBeTruthy();
  });
});
