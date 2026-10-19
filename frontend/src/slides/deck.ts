/* Moving through the slides: which slide the address points to, and what keys and swipes do. */

export type Move = "next" | "previous" | "first" | "last";

/** A finger has to travel this far sideways for a swipe. */
const SWIPE_PX = 40;

/** The slide (from 0) a location hash points to: "#3" is the third. Anything else is the first. */
export function slideFromHash(hash: string, count: number): number {
  const n = Number(hash.replace(/^#/, ""));
  if (!Number.isInteger(n) || n < 1) return 0;
  return Math.min(n, count) - 1;
}

/** The location hash for a slide (from 0). */
export function hashFor(index: number): string {
  return `#${index + 1}`;
}

/** The slide a move leads to, staying within the deck. */
export function moveTo(move: Move, index: number, count: number): number {
  switch (move) {
    case "next":
      return Math.min(index + 1, count - 1);
    case "previous":
      return Math.max(index - 1, 0);
    case "first":
      return 0;
    case "last":
      return count - 1;
  }
}

/** The move a key makes, or null for keys the deck leaves alone. */
export function keyMove(key: string, shift: boolean): Move | null {
  switch (key) {
    case "ArrowRight":
    case "ArrowDown":
    case "PageDown":
      return "next";
    case "ArrowLeft":
    case "ArrowUp":
    case "PageUp":
      return "previous";
    case " ":
      return shift ? "previous" : "next";
    case "Home":
      return "first";
    case "End":
      return "last";
    default:
      return null;
  }
}

/** The move a swipe makes: far enough sideways, and more sideways than up or down. A swipe to the
    left brings in the next slide. */
export function swipeMove(dx: number, dy: number): Move | null {
  if (Math.abs(dx) < SWIPE_PX || Math.abs(dx) < 1.5 * Math.abs(dy)) return null;
  return dx < 0 ? "next" : "previous";
}
