// Regenerate the walkthrough (docs/walkthrough.md): one short animated clip for each situation the app handles.
//
// Needs, running locally: the API (`uv run uvicorn floodroute.api.app:app --port 8010` in backend/)
// and the web dev server (`npm run dev`, with FLOODROUTE_API_URL pointing at that API).
// Also needs Google Chrome (or CHROME_PATH) and ffmpeg on the PATH.
//
//   npm run capture                       # every clip
//   npm run capture -- choose cut-off     # only the named clips (see CLIPS below)

import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import puppeteer from "puppeteer-core";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const OUT = path.join(ROOT, "docs", "images");
const APP = process.env.APP_URL ?? "http://localhost:5174";
const CHROME =
  process.env.CHROME_PATH ??
  {
    darwin: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    linux: "/usr/bin/google-chrome",
    win32: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  }[process.platform];

// Places used in the clips: [lat, lon].
const BOYD_VILLAGE = [-37.82613, 144.96126];
const CROWN = [-37.8224, 144.96048];
const CROWN_WEST = [-37.82506, 144.95828]; // inside the Crown Entertainment Complex
const SOUTHBANK_EAST = [-37.826185, 144.963614];
const SOUTH_WHARF = [-37.824086, 144.954684];
const STURT_STREET = [-37.82579, 144.961159];
const SOUTHBANK_PROMENADE = [-37.819892, 144.967703];
const NEAR_CROWN = [-37.82228, 144.95793]; // dry ground; under heavy flooding every way south is too deep
const SOUTH_OF_CROWN = [-37.82704, 144.9541];
// Either side of an 8.3% path on the promenade: 109 m on foot, 429 m round it in a wheelchair.
const PROMENADE_WEST = [-37.820479, 144.963567];
const PROMENADE_EAST = [-37.820245, 144.964435];
// Under moderate flooding with a knee limit, each route preference gives a different route here.
const PREFERENCE_START = [-37.825239, 144.965677];
const CROWN_PROMENADE_HOTEL = [-37.824044, 144.960144];

const DESKTOP = { width: 1280, height: 800, deviceScaleFactor: 1 };
const PHONE = { width: 390, height: 844, deviceScaleFactor: 1, isMobile: true, hasTouch: true };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function open(browser, viewport) {
  const page = await browser.newPage();
  await page.setViewport(viewport);
  // Every clip starts in English, whatever an earlier clip chose (the choice is kept in storage).
  await page.evaluateOnNewDocument(() => {
    try {
      localStorage.setItem("floodroute.language", "en");
    } catch {
      // no storage: the browser's language, English here, decides
    }
  });
  await page.goto(APP, { waitUntil: "networkidle0" });
  await page.waitForFunction(() => window.__floodrouteMap && document.querySelector(".levels button"));
  await mapIdle(page);
  return page;
}

function mapIdle(page) {
  return page.evaluate(
    () =>
      new Promise((resolve) => {
        const m = window.__floodrouteMap;
        if (m.loaded()) return resolve();
        m.once("idle", resolve);
        setTimeout(resolve, 15000);
      }),
  );
}

/** Choose `value` in the select that offers `marker` (a body part, or a mobility aid). */
async function choose(page, marker, value) {
  await page.evaluate(
    (marker, value) => {
      const select = [...document.querySelectorAll("select")].find((s) => [...s.options].some((o) => o.value === marker));
      Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value").set.call(select, value);
      select.dispatchEvent(new Event("change", { bubbles: true }));
    },
    marker,
    value,
  );
}

const setWading = (page, wading) => choose(page, "knee", wading);
const setAid = (page, aid) => choose(page, "manual_wheelchair", aid);

/** Screen position of a place on the map. */
function mapPoint(page, [lat, lon]) {
  return page.evaluate(
    (lat, lon) => {
      const m = window.__floodrouteMap;
      const p = m.project([lon, lat]);
      const r = m.getCanvas().getBoundingClientRect();
      return { x: r.left + p.x, y: r.top + p.y };
    },
    lat,
    lon,
  );
}

/** Pan and zoom the map so both places are in view. */
async function showPlaces(page, a, b, padding = 140) {
  await page.evaluate(
    (a, b, padding) =>
      window.__floodrouteMap.fitBounds(
        [
          [Math.min(a[1], b[1]), Math.min(a[0], b[0])],
          [Math.max(a[1], b[1]), Math.max(a[0], b[0])],
        ],
        { padding, duration: 900 },
      ),
    a,
    b,
    padding,
  );
  await sleep(1100);
  await mapIdle(page);
}

function nextStepText(page) {
  return page.evaluate(() => document.querySelector(".next")?.innerText ?? "");
}

async function waitForNewPlan(page, previous) {
  await page.waitForFunction(
    (prev) => {
      const text = document.querySelector(".next")?.innerText;
      return text && text !== prev;
    },
    { timeout: 20000 },
    previous,
  );
  await sleep(800); // the map zooms to the trip
  await mapIdle(page);
}

function showResults(page, phone) {
  return page.evaluate((phone) => {
    const panel = document.querySelector(".panel");
    const target = document.querySelector(".results") ?? document.querySelector(".next");
    // On a phone the sheet's sticky handle covers the top of the panel.
    if (target) panel.scrollTo({ top: target.offsetTop - (phone ? 56 : 12), behavior: "smooth" });
  }, phone);
}

// A visible pointer that follows the mouse and pulses on clicks; headless recordings have none. On a
// phone only the pulse shows, like a tap.
const POINTER = `
  #pointer { position: fixed; z-index: 99999; width: 26px; height: 26px; margin: -4px 0 0 -4px; pointer-events: none;
    transition: transform 0.08s; }
  #pointer.down { transform: scale(0.85); }
  #pointer.touch svg { display: none; }
  #pointer::after { content: ""; position: absolute; left: -10px; top: -10px; width: 28px; height: 28px; border-radius: 50%;
    border: 3px solid rgba(123, 44, 191, 0.8); opacity: 0; }
  #pointer.down::after { animation: pulse 0.5s ease-out; }
  @keyframes pulse { from { opacity: 1; transform: scale(0.4); } to { opacity: 0; transform: scale(1.4); } }`;
const POINTER_SVG =
  '<svg viewBox="0 0 26 26" width="26" height="26"><path d="M3 2 L3 21 L8 16 L12 24 L15 22.5 L11 15 L18 15 Z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';

async function addPointer(page, touch) {
  await page.addStyleTag({ content: POINTER });
  await page.evaluate(
    (svg, touch) => {
      const el = document.createElement("div");
      el.id = "pointer";
      if (touch) el.classList.add("touch");
      el.innerHTML = svg;
      el.style.left = `${innerWidth / 2}px`;
      el.style.top = `${innerHeight / 2}px`;
      document.body.appendChild(el);
      addEventListener(
        "mousemove",
        (e) => {
          el.style.left = `${e.clientX}px`;
          el.style.top = `${e.clientY}px`;
        },
        true,
      );
      addEventListener(
        "mousedown",
        () => {
          el.classList.remove("down");
          void el.offsetWidth;
          el.classList.add("down");
        },
        true,
      );
      addEventListener("mouseup", () => setTimeout(() => el.classList.remove("down"), 300), true);
    },
    POINTER_SVG,
    touch,
  );
}

async function clickAt(page, { x, y }) {
  await page.mouse.move(x, y, { steps: 25 });
  await sleep(200);
  await page.mouse.down();
  await sleep(90);
  await page.mouse.up();
}

/** Click the element whose text starts with `text`, bringing it into view first. */
async function clickButton(page, selector, text) {
  const box = await page.evaluate(
    (selector, text) => {
      const el = [...document.querySelectorAll(selector)].find((b) => b.innerText.trim().startsWith(text));
      if (!el) throw new Error(`no ${selector} starting with "${text}"`);
      el.scrollIntoView({ block: "nearest", behavior: "instant" });
      const r = el.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    },
    selector,
    text,
  );
  await sleep(250);
  await clickAt(page, box);
}

async function pickLevel(page, level) {
  await clickButton(page, ".levels button", level);
  await sleep(600);
  await mapIdle(page);
}

/** Set the start and the destination by clicking the map, and wait for the plan. The map is framed
 * on both places before recording (see `frame`), so the clip does not spend frames on panning. */
async function planTrip(page, from, to, phone = false) {
  const before = await nextStepText(page);
  await clickAt(page, await mapPoint(page, from));
  await sleep(600);
  await clickAt(page, await mapPoint(page, to));
  await waitForNewPlan(page, before);
  await showResults(page, phone);
}

/** Choose a mobility aid in the traveller panel, with the pointer on it, and wait for the new plan. */
async function switchAid(page, aid) {
  const before = await nextStepText(page);
  const box = await page.evaluate(() => {
    const select = [...document.querySelectorAll("select")].find((s) => [...s.options].some((o) => o.value === "manual_wheelchair"));
    select.scrollIntoView({ block: "center", behavior: "instant" });
    const r = select.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  });
  await page.mouse.move(box.x, box.y, { steps: 25 });
  await sleep(500);
  await setAid(page, aid);
  await waitForNewPlan(page, before);
  await sleep(1400); // the panel now shows the device's levels
  await showResults(page, false);
}

/** Choose a device and one of its levels (an index into its levels), then wait for the new plan. */
async function switchDevice(page, aid, level) {
  await switchAid(page, aid);
  await page.evaluate(() =>
    [...document.querySelectorAll("select")].find((s) => [...s.options].some((o) => o.value === "0"))?.scrollIntoView({ block: "center" }),
  );
  await sleep(600);
  await choose(page, "0", String(level));
  await sleep(2600); // the plan for the new level
  await mapIdle(page);
  await showResults(page, false);
}

/** Type a place into the start (0) or destination (1) search box and pick the first match. */
async function searchPlace(page, which, text) {
  const box = await page.evaluate((which) => {
    const input = document.querySelectorAll(".place")[which].querySelector("form.search input");
    input.scrollIntoView({ block: "nearest" });
    const r = input.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  }, which);
  await clickAt(page, box);
  await page.keyboard.type(text, { delay: 70 });
  await sleep(300);
  await page.keyboard.press("Enter");
  await page.waitForSelector(".hits button", { timeout: 20000 });
  await sleep(800);
  await clickButton(page, ".hits button", text);
}

/** Pick a route preference and wait for the plan it gives. */
async function pickPreference(page, label) {
  const before = await nextStepText(page);
  await clickButton(page, ".pref", label);
  await waitForNewPlan(page, before);
  await showResults(page, false);
}

/** Choose a language from the menu at the top of the panel, with the pointer on it, and wait for
 * the plan in its words. */
async function switchLanguage(page, lang) {
  const before = await nextStepText(page);
  const box = await page.evaluate(() => {
    document.querySelector(".panel").scrollTo({ top: 0, behavior: "smooth" });
    const r = document.querySelector(".lang-switch select").getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  });
  await sleep(500);
  await page.mouse.move(box.x, box.y, { steps: 20 });
  await sleep(400);
  await choose(page, "ko", lang);
  await waitForNewPlan(page, before);
  await sleep(600);
}

async function useLimit(page) {
  const before = await nextStepText(page);
  await clickButton(page, ".choice button.button", "Use this limit");
  await waitForNewPlan(page, before);
  await showResults(page, false);
}

// One clip per situation, in the order docs/walkthrough.md shows them. Before recording, the map is framed on
// `frame` and `setup` runs.
const CLIPS = {
  "flood-levels": {
    run: async (page) => {
      for (const level of ["Light", "Moderate", "Heavy", "Extreme"]) {
        await pickLevel(page, level);
        await sleep(1300);
      }
    },
  },
  search: {
    setup: (page) => setWading(page, "ankle"),
    run: async (page) => {
      await pickLevel(page, "Light");
      await searchPlace(page, 0, "Eureka Tower");
      await sleep(900);
      const before = await nextStepText(page);
      await searchPlace(page, 1, "Crown Melbourne");
      await waitForNewPlan(page, before);
      await showResults(page, false);
      await sleep(3000);
    },
  },
  detour: {
    frame: [SOUTHBANK_EAST, SOUTH_WHARF],
    setup: (page) => setWading(page, "ankle"),
    run: async (page) => {
      await pickLevel(page, "Light");
      await planTrip(page, SOUTHBANK_EAST, SOUTH_WHARF);
      await sleep(2000);
      await clickButton(page, ".compare-row", "Shortest, ignoring");
      await sleep(2000);
      await clickButton(page, ".compare-row", "Recommended");
      await sleep(1800);
    },
  },
  preferences: {
    frame: [PREFERENCE_START, CROWN_PROMENADE_HOTEL],
    setup: (page) => setWading(page, "knee"),
    run: async (page) => {
      await pickLevel(page, "Moderate");
      await planTrip(page, PREFERENCE_START, CROWN_PROMENADE_HOTEL);
      await sleep(2200);
      await pickPreference(page, "Shortest");
      await sleep(2200);
      await pickPreference(page, "Stay as dry as possible");
      await sleep(2600);
    },
  },
  choose: {
    frame: [BOYD_VILLAGE, CROWN],
    setup: (page) => setWading(page, "mid_calf"),
    run: async (page) => {
      await pickLevel(page, "Moderate");
      await planTrip(page, BOYD_VILLAGE, CROWN);
      await sleep(2200);
      await clickButton(page, ".choice-main", "Accept water");
      await sleep(1800);
      await useLimit(page);
      await sleep(2200);
    },
  },
  shelter: {
    frame: [NEAR_CROWN, SOUTH_OF_CROWN],
    setup: (page) => setWading(page, "mid_calf"),
    run: async (page) => {
      await pickLevel(page, "Heavy");
      await planTrip(page, NEAR_CROWN, SOUTH_OF_CROWN);
      await sleep(3200);
    },
  },
  "deep-water": {
    frame: [STURT_STREET, SOUTHBANK_PROMENADE],
    setup: (page) => setWading(page, "mid_calf"),
    run: async (page) => {
      await pickLevel(page, "Heavy");
      await planTrip(page, STURT_STREET, SOUTHBANK_PROMENADE);
      await sleep(3400);
    },
  },
  "cut-off": {
    frame: [BOYD_VILLAGE, CROWN],
    setup: (page) => setWading(page, "ankle"),
    run: async (page) => {
      await pickLevel(page, "Extreme");
      await planTrip(page, BOYD_VILLAGE, CROWN);
      await sleep(3400);
    },
  },
  wheelchair: {
    frame: [CROWN_WEST, BOYD_VILLAGE],
    setup: (page) => setAid(page, "manual_wheelchair"),
    run: async (page) => {
      await pickLevel(page, "Light");
      await planTrip(page, CROWN_WEST, BOYD_VILLAGE);
      await sleep(2400);
      await useLimit(page);
      await sleep(2200);
    },
  },
  "mobility-aids": {
    frame: [CROWN_WEST, BOYD_VILLAGE],
    setup: async (page) => {
      await setAid(page, "powered_wheelchair");
      await sleep(300);
      await choose(page, "0", "1"); // well below the chassis, 5 cm
    },
    run: async (page) => {
      await pickLevel(page, "Light");
      await planTrip(page, CROWN_WEST, BOYD_VILLAGE);
      await sleep(2600);
      await switchDevice(page, "mobility_scooter", 1); // a shallow puddle, 2.5 cm: the scooter's cap
      await sleep(3200);
    },
  },
  "steep-path": {
    frame: [PROMENADE_WEST, PROMENADE_EAST],
    setup: (page) => setWading(page, "ankle"),
    run: async (page) => {
      await planTrip(page, PROMENADE_WEST, PROMENADE_EAST);
      await sleep(3000);
      await switchAid(page, "manual_wheelchair");
      await sleep(3400);
    },
  },
  "get-help": {
    run: async (page) => {
      await sleep(600);
      await clickButton(page, ".get-help-button", "🆘");
      await sleep(1600);
      await clickButton(page, ".get-help-panel button", "📣");
      await sleep(2400);
      await clickButton(page, ".get-help-panel button.link", "Undo");
      await sleep(1400);
    },
  },
  languages: {
    frame: [BOYD_VILLAGE, CROWN],
    setup: (page) => setWading(page, "mid_calf"),
    run: async (page) => {
      await pickLevel(page, "Moderate");
      await planTrip(page, BOYD_VILLAGE, CROWN);
      await sleep(1600);
      for (const lang of ["es", "zh-Hans", "hi", "ko"]) {
        await switchLanguage(page, lang);
        await sleep(2400);
      }
    },
  },
  phone: {
    frame: [BOYD_VILLAGE, CROWN],
    viewport: PHONE,
    setup: (page) => setWading(page, "mid_calf"),
    run: async (page) => {
      await pickLevel(page, "Moderate");
      await planTrip(page, BOYD_VILLAGE, CROWN, true);
      await sleep(1800);
      await clickButton(page, ".sheet-handle", "Show details");
      await sleep(2600);
    },
  },
};

/** A small looping GIF: 8 frames a second, one palette for the whole clip. */
function toGif(video, out, width) {
  execFileSync("ffmpeg", [
    "-y",
    "-loglevel",
    "error",
    "-i",
    video,
    "-vf",
    `fps=8,scale=${width}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=80:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle`,
    "-loop",
    "0",
    out,
  ]);
}

async function record(browser, name, clip) {
  const tmp = mkdtempSync(path.join(tmpdir(), "clip-"));
  try {
    const viewport = clip.viewport ?? DESKTOP;
    const page = await open(browser, viewport);
    // Keep both places clear of the legend (bottom left on a desktop) and of Get help (top left).
    const padding = viewport.isMobile ? { top: 70, bottom: 60, left: 40, right: 40 } : { top: 90, bottom: 220, left: 90, right: 90 };
    if (clip.frame) await showPlaces(page, ...clip.frame, padding);
    await clip.setup?.(page);
    await addPointer(page, !!viewport.isMobile);
    const video = path.join(tmp, `${name}.webm`);
    const recorder = await page.screencast({ path: video });
    await sleep(900);
    await clip.run(page);
    await recorder.stop();
    await page.close();
    toGif(video, path.join(OUT, `${name}.gif`), viewport.isMobile ? 340 : 640);
    console.log(`saved ${name}.gif`);
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

const names = process.argv.slice(2);
const unknown = names.filter((n) => !(n in CLIPS));
if (unknown.length) {
  console.error(`Unknown clip(s): ${unknown.join(", ")}. Clips: ${Object.keys(CLIPS).join(", ")}`);
  process.exit(1);
}
const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
try {
  for (const name of names.length ? names : Object.keys(CLIPS)) await record(browser, name, CLIPS[name]);
} finally {
  await browser.close();
}
