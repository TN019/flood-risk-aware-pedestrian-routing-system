// Regenerate the README images: five screenshots and the animated walkthrough.
//
// Needs, running locally: the API (`uv run uvicorn floodroute.api.app:app --port 8010` in backend/)
// and the web dev server (`npm run dev`, with FLOODROUTE_API_URL pointing at that API).
// Also needs Google Chrome (or CHROME_PATH) and ffmpeg on the PATH.
//
//   npm run capture                    # everything
//   npm run capture -- screenshots     # only the screenshots
//   npm run capture -- walkthrough     # only the animated walkthrough

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

// Places used in the images: [lat, lon].
const BOYD_VILLAGE = [-37.82613, 144.96126];
const CROWN = [-37.8224, 144.96048];
const CROWN_WEST = [-37.82506, 144.95828]; // inside the Crown Entertainment Complex
const SOUTHBANK_EAST = [-37.826185, 144.963614];
const SOUTH_WHARF = [-37.824086, 144.954684];
const STURT_STREET = [-37.82579, 144.961159];
const SOUTHBANK_PROMENADE = [-37.819892, 144.967703];

const DESKTOP = { width: 1280, height: 800, deviceScaleFactor: 1.25 }; // 1600 px wide images
const PHONE = { width: 390, height: 844, deviceScaleFactor: 1.5, isMobile: true, hasTouch: true };

const SCREENSHOTS = [
  { file: "detour.jpg", viewport: DESKTOP, level: "Light", wading: "ankle", from: SOUTHBANK_EAST, to: SOUTH_WHARF },
  { file: "choose.jpg", viewport: DESKTOP, level: "Moderate", wading: "mid_calf", from: BOYD_VILLAGE, to: CROWN },
  { file: "emergency.jpg", viewport: DESKTOP, level: "Heavy", wading: "mid_calf", from: STURT_STREET, to: SOUTHBANK_PROMENADE },
  { file: "phone.jpg", viewport: PHONE, level: "Moderate", wading: "mid_calf", from: BOYD_VILLAGE, to: CROWN },
  { file: "wheelchair.jpg", viewport: DESKTOP, level: "Light", aid: "manual_wheelchair", from: CROWN_WEST, to: BOYD_VILLAGE },
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function open(browser, viewport) {
  const page = await browser.newPage();
  await page.setViewport(viewport);
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
async function showPlaces(page, a, b) {
  await page.evaluate(
    (a, b) =>
      window.__floodrouteMap.fitBounds(
        [
          [Math.min(a[1], b[1]), Math.min(a[0], b[0])],
          [Math.max(a[1], b[1]), Math.max(a[0], b[0])],
        ],
        { padding: 140, duration: 900 },
      ),
    a,
    b,
  );
  await sleep(1100);
  await mapIdle(page);
}

function nextStepText(page) {
  return page.evaluate(() => document.querySelector(".next")?.innerText ?? "");
}

async function waitForNewPlan(page, previous) {
  await page.waitForFunction((prev) => {
    const text = document.querySelector(".next")?.innerText;
    return text && text !== prev;
  }, { timeout: 20000 }, previous);
  await sleep(800); // the map zooms to the trip
  await mapIdle(page);
}

function showResults(page, phone, smooth = false) {
  return page.evaluate(
    (phone, smooth) => {
      const panel = document.querySelector(".panel");
      const target = document.querySelector(".results") ?? document.querySelector(".next");
      // On a phone the sheet's sticky handle covers the top of the panel.
      if (target) panel.scrollTo({ top: target.offsetTop - (phone ? 56 : 12), behavior: smooth ? "smooth" : "instant" });
    },
    phone,
    smooth,
  );
}

async function screenshots(browser) {
  for (const shot of SCREENSHOTS) {
    const page = await open(browser, shot.viewport);
    if (shot.aid) await setAid(page, shot.aid);
    else await setWading(page, shot.wading);
    await page.evaluate((level) => [...document.querySelectorAll(".levels button")].find((b) => b.textContent === level).click(), shot.level);
    await sleep(1500);
    const before = await nextStepText(page);
    for (const place of [shot.from, shot.to]) {
      const { x, y } = await mapPoint(page, place);
      await page.mouse.click(x, y);
      await sleep(400);
    }
    await waitForNewPlan(page, before);
    await showResults(page, !!shot.viewport.isMobile);
    await sleep(600);
    await page.screenshot({ path: path.join(OUT, shot.file), type: "jpeg", quality: 82 });
    console.log("saved", shot.file);
    await page.close();
  }
}

// A visible pointer that follows the mouse and pulses on clicks; headless screenshots have none.
const POINTER = `
  #pointer { position: fixed; z-index: 99999; width: 26px; height: 26px; margin: -4px 0 0 -4px; pointer-events: none;
    transition: transform 0.08s; }
  #pointer.down { transform: scale(0.85); }
  #pointer::after { content: ""; position: absolute; left: -10px; top: -10px; width: 28px; height: 28px; border-radius: 50%;
    border: 3px solid rgba(123, 44, 191, 0.8); opacity: 0; }
  #pointer.down::after { animation: pulse 0.5s ease-out; }
  @keyframes pulse { from { opacity: 1; transform: scale(0.4); } to { opacity: 0; transform: scale(1.4); } }`;
const POINTER_SVG =
  '<svg viewBox="0 0 26 26" width="26" height="26"><path d="M3 2 L3 21 L8 16 L12 24 L15 22.5 L11 15 L18 15 Z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';

async function addPointer(page) {
  await page.addStyleTag({ content: POINTER });
  await page.evaluate((svg) => {
    const el = document.createElement("div");
    el.id = "pointer";
    el.innerHTML = svg;
    el.style.left = "640px";
    el.style.top = "400px";
    document.body.appendChild(el);
    addEventListener("mousemove", (e) => {
      el.style.left = `${e.clientX}px`;
      el.style.top = `${e.clientY}px`;
    }, true);
    addEventListener("mousedown", () => {
      el.classList.remove("down");
      void el.offsetWidth;
      el.classList.add("down");
    }, true);
    addEventListener("mouseup", () => setTimeout(() => el.classList.remove("down"), 300), true);
  }, POINTER_SVG);
}

async function clickAt(page, { x, y }) {
  await page.mouse.move(x, y, { steps: 25 });
  await sleep(200);
  await page.mouse.down();
  await sleep(90);
  await page.mouse.up();
}

/** Click the button whose text starts with `text`, bringing it into view first. */
async function clickButton(page, selector, text) {
  const box = await page.evaluate(
    (selector, text) => {
      const el = [...document.querySelectorAll(selector)].find((b) => b.innerText.trim().startsWith(text));
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

async function walkthrough(browser) {
  const tmp = mkdtempSync(path.join(tmpdir(), "walkthrough-"));
  try {
    const page = await open(browser, { width: 1280, height: 800, deviceScaleFactor: 1 });
    await setWading(page, "mid_calf");
    await addPointer(page);
    const video = path.join(tmp, "walkthrough.webm");
    const recorder = await page.screencast({ path: video });
    await sleep(1200);

    // 1. Light flooding: Boyd Village to Crown Melbourne.
    await clickButton(page, ".levels button", "Light");
    await sleep(900);
    let before = await nextStepText(page);
    await clickAt(page, await mapPoint(page, BOYD_VILLAGE));
    await sleep(700);
    await clickAt(page, await mapPoint(page, CROWN));
    await waitForNewPlan(page, before);
    await showResults(page, false, true);
    await sleep(2200);

    // 2. Moderate flooding: no route fits a mid-calf limit, so a choice.
    before = await nextStepText(page);
    await clickButton(page, ".levels button", "Moderate");
    await waitForNewPlan(page, before);
    await showResults(page, false, true);
    await sleep(2600);

    // 3. Look at accepting water up to the knee, then take that limit.
    await clickButton(page, ".choice-main", "Accept water");
    await sleep(800);
    await mapIdle(page);
    await sleep(1800);
    before = await nextStepText(page);
    await clickButton(page, ".choice button.button", "Use this limit");
    await waitForNewPlan(page, before);
    await showResults(page, false, true);
    await sleep(2200);

    // 4. Heavy flooding, starting in deep water: emergency help and the way to shelter.
    await clickButton(page, ".levels button", "Heavy");
    await sleep(600);
    before = await nextStepText(page);
    await clickButton(page, "button", "Clear");
    await sleep(500);
    await showPlaces(page, STURT_STREET, SOUTHBANK_PROMENADE);
    await clickAt(page, await mapPoint(page, STURT_STREET));
    await sleep(700);
    await clickAt(page, await mapPoint(page, SOUTHBANK_PROMENADE));
    await waitForNewPlan(page, before);
    await showResults(page, false, true);
    await sleep(3200);

    await recorder.stop();
    await page.close();
    // A small, looping GIF: 8 frames a second, 760 px wide, one palette for the whole clip.
    execFileSync("ffmpeg", [
      "-y",
      "-loglevel", "error",
      "-i", video,
      "-vf", "fps=8,scale=760:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle",
      "-loop", "0",
      path.join(OUT, "walkthrough.gif"),
    ]);
    console.log("saved walkthrough.gif");
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

const which = process.argv[2] ?? "all";
const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
try {
  if (which === "all" || which === "screenshots") await screenshots(browser);
  if (which === "all" || which === "walkthrough") await walkthrough(browser);
} finally {
  await browser.close();
}
