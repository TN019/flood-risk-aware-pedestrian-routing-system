/* What the /slides page says: the walkthrough (docs/walkthrough.md) as slides to present, one per
   clip and in the same order, with each caption cut down to a line or two. Keep the two in step. */

export type FloodLevel = "none" | "light" | "moderate" | "heavy" | "extreme";

export const FLOOD_LABEL: Record<FloodLevel, string> = {
  none: "No flooding",
  light: "Light flooding",
  moderate: "Moderate flooding",
  heavy: "Heavy flooding",
  extreme: "Extreme flooding",
};

export type Clip = {
  /** The clip's file in docs/images, without ".gif". */
  name: string;
  title: string;
  text: string;
  /** What the clip shows, for anyone who cannot see it. */
  alt: string;
  /** The flood level the clip is recorded at, if it is at one. */
  flood?: FloodLevel;
  /** The rest of the situation: the traveller's limit, device or starting point. */
  tags?: string[];
  /** Recorded on a phone, so shown in a phone's frame. */
  phone?: boolean;
};

export const INTRO = {
  name: "Southbank Flood Routes",
  title: "Flood Risk-Aware Pedestrian Routing",
  text: "Walking routes through Southbank, Melbourne that never cross water deeper than the traveller accepts, and weigh the rest against distance.",
};

export const CLIPS: Clip[] = [
  {
    name: "flood-levels",
    title: "Flood levels",
    text: "Five levels, from none to extreme: the typical water on flooded footpaths rises from the ankle (6 cm) to above the hip (99 cm).",
    alt: "The water on the map rising from light to extreme flooding",
  },
  {
    name: "search",
    title: "Finding a place",
    text: "Search by name instead of clicking the map: from Eureka Tower to Crown Melbourne is 570 m, and dry.",
    alt: "Searching for Eureka Tower and Crown Melbourne, then the route between them",
    flood: "light",
    tags: ["Ankle limit"],
  },
  {
    name: "detour",
    title: "Around the water",
    text: "The shortest way crosses water of unknown depth, so the recommended route walks 12 m further to stay within the limit.",
    alt: "The recommended route, then the flood-ignoring shortest way it avoids",
    flood: "light",
    tags: ["Ankle limit"],
  },
  {
    name: "preferences",
    title: "Route preference",
    text: "Water within the limit is weighed against distance, never forbidden: Shortest walks 604 m with 100 m in water, Stay as dry as possible 821 m with 55 m.",
    alt: "The same trip with the Balanced, Shortest and Stay as dry as possible preferences",
    flood: "moderate",
    tags: ["Knee limit"],
  },
  {
    name: "choose",
    title: "No route fits: a choice",
    text: "Every way crosses at least 32 cm, so the choice is to accept water up to the knee or to stay inside. The knee limit gives a route.",
    alt: "Two choices, then the route with the knee limit",
    flood: "moderate",
    tags: ["Mid-calf limit, 28 cm"],
  },
  {
    name: "shelter",
    title: "Go to a shelter",
    text: "Every way to the destination crosses at least 68 cm, more than the 50 cm anyone is routed through. The nearest shelter is 140 m away, and dry.",
    alt: "The way to the nearest shelter when the destination is out of reach",
    flood: "heavy",
    tags: ["From dry ground"],
  },
  {
    name: "deep-water",
    title: "Standing in deep water",
    text: "Emergency help comes first, then the nearest shelter by the shallowest way out.",
    alt: "Emergency help and the shallowest way to shelter from deep water",
    flood: "heavy",
    tags: ["Starting in 67 cm"],
  },
  {
    name: "cut-off",
    title: "Cut off inside a building",
    text: "Every way to Crown Melbourne crosses at least 147 cm. Stay inside and move to a higher floor if water comes in; emergency help is available.",
    alt: "Emergency help for a traveller cut off by deep water inside a building",
    flood: "extreme",
    tags: ["Inside a building"],
  },
  {
    name: "wheelchair",
    title: "With a wheelchair",
    text: "Every step-free way crosses 3 cm, above the lowest level (2 cm), so the choice is the next level, 5 cm, or staying inside. No steps, and no paths steeper than 1:14.",
    alt: "The next level of the device, then the step-free route with it",
    flood: "light",
    tags: ["Manual wheelchair"],
  },
  {
    name: "mobility-aids",
    title: "Powered wheelchair and scooter",
    text: "On the same trip, a powered wheelchair at its 5 cm level has a 379 m route. A mobility scooter is capped at 2.5 cm, so it stays inside.",
    alt: "A powered wheelchair's route, then no route for a mobility scooter at its cap",
    flood: "light",
    tags: ["Powered wheelchair", "Mobility scooter"],
  },
  {
    name: "steep-path",
    title: "Steep paths",
    text: "On foot the route is 109 m, over a path at 8.3%. With a wheelchair it goes round, 429 m: no path steeper than 1:14 (7.1%).",
    alt: "The route on foot over an 8.3% path, then the wheelchair route around it",
    flood: "none",
    tags: ["On foot", "Manual wheelchair"],
  },
  {
    name: "get-help",
    title: "Get help, at any time",
    text: "Always on the map: call 000 if a life is in danger, VICSES 132 500 for flood or storm help, or alert people nearby (simulated, with undo).",
    alt: "Get help: calls to 000 and VICSES, and an SOS alert with undo",
  },
  {
    name: "languages",
    title: "In your language",
    text: "English, Spanish, Chinese, Hindi and Korean, from the 2021 Census: the same plan in each, with numbers, places and phone numbers unchanged.",
    alt: "The same trip in Spanish, Chinese, Hindi and Korean",
    flood: "moderate",
    tags: ["Mid-calf limit"],
  },
  {
    name: "phone",
    title: "On a phone",
    text: "The map sits above a sheet that slides up; the legend starts folded.",
    alt: "A choice on a phone, with the sheet slid up",
    phone: true,
  },
];

/** The last slide, only when the deck is opened at a public address: a QR code for each page, at
    the address the deck itself was opened at. */
export const SHARE = {
  title: "Try it yourself",
  pages: [
    { path: "/", label: "The app" },
    { path: "/reference/", label: "Sources and references" },
    { path: "/benchmark/", label: "How it is tested" },
  ],
  notice: "Routes are guidance, not a guarantee. In an emergency, call 000.",
};

// The clips are bundled from docs/images when the client is built, rather than copied next to it.
const FILES = import.meta.glob<string>("../../../docs/images/*.gif", { eager: true, query: "?url", import: "default" });

/** Where a clip is served from, or undefined if docs/images has no such clip. */
export function clipUrl(name: string): string | undefined {
  return FILES[`../../../docs/images/${name}.gif`];
}
