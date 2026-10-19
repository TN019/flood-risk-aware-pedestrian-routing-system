import qrcode from "qrcode-generator";
import { type MouseEvent, type ReactNode, type TouchEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { type Clip, CLIPS, clipUrl, FLOOD_LABEL, INTRO, SHARE } from "./content";
import { hashFor, keyMove, type Move, moveTo, slideFromHash, swipeMove } from "./deck";
import { isLocalHost } from "./host";

/** Opened at a public address, so the deck ends with QR codes for the audience to open it too. */
const PUBLIC = !isLocalHost(window.location.hostname);

/** The title, a slide per clip, and at a public address the QR codes. */
const COUNT = CLIPS.length + (PUBLIC ? 2 : 1);

const TITLES = [INTRO.title, ...CLIPS.map((c) => c.title), SHARE.title];

/** The walkthrough as slides to present. Reached only by its address, /slides; the address keeps
    the slide shown (/slides#3), so a reload stays on it. */
export function SlidesPage() {
  const [index, setIndex] = useState(() => slideFromHash(window.location.hash, COUNT));
  const fullscreen = useFullscreen();
  const toggleFullscreen = fullscreen.toggle;
  const touch = useRef<{ x: number; y: number } | null>(null);

  const move = useCallback((m: Move) => setIndex((i) => moveTo(m, i, COUNT)), []);

  useEffect(() => {
    const hash = hashFor(index);
    if (window.location.hash !== hash) window.history.replaceState(null, "", hash);
  }, [index]);

  useEffect(() => {
    const onHash = () => setIndex(slideFromHash(window.location.hash, COUNT));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      // Space and Enter on a focused button press it.
      if (e.target instanceof HTMLButtonElement && (e.key === " " || e.key === "Enter")) return;
      if (e.key === "f" || e.key === "F") return toggleFullscreen();
      const m = keyMove(e.key, e.shiftKey);
      if (!m) return;
      e.preventDefault();
      move(m);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [move, toggleFullscreen]);

  // A click or tap on the left half goes back, on the right half forward.
  const onClick = (e: MouseEvent<HTMLElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    move(e.clientX - box.left < box.width / 2 ? "previous" : "next");
  };

  const onTouchStart = (e: TouchEvent) => {
    const t = e.touches[0];
    touch.current = e.touches.length === 1 ? { x: t.clientX, y: t.clientY } : null;
  };

  const onTouchEnd = (e: TouchEvent) => {
    const start = touch.current;
    touch.current = null;
    const t = e.changedTouches[0];
    if (!start || !t) return;
    const m = swipeMove(t.clientX - start.x, t.clientY - start.y);
    if (m) move(m);
  };

  return (
    <main className="deck" aria-roledescription="slide deck" aria-label="Walkthrough">
      <div className="deck-stage" onClick={onClick} onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
        <div className="deck-track" style={{ transform: `translateX(${-100 * index}%)` }}>
          <Slide at={0} index={index} className="slide-dark slide-intro">
            <Waves />
            <div className="intro">
              <p className="lockup">
                <img src="/icon.svg" alt="" width={40} height={40} />
                {INTRO.name}
              </p>
              <h1>{INTRO.title}</h1>
              <p className="lede">{INTRO.text}</p>
            </div>
            <p className="deck-hint">
              <span className="hint-keys">
                Press <kbd>→</kbd> or <kbd>Space</kbd> to begin
              </span>
              <span className="hint-touch">Swipe or tap to begin</span>
            </p>
          </Slide>

          {CLIPS.map((clip, i) => (
            <Slide key={clip.name} at={i + 1} index={index} className={`slide-clip${clip.phone ? " clip-phone" : ""}`}>
              <ClipSlide clip={clip} number={i + 1} current={index === i + 1} near={i + 1 >= index - 1 && i + 1 <= index + 2} />
            </Slide>
          ))}

          {PUBLIC && (
            <Slide at={COUNT - 1} index={index} className="slide-dark slide-share">
              <Waves />
              <div className="share">
                <h2>{SHARE.title}</h2>
                <ul className="qr-codes">
                  {SHARE.pages.map((p) => (
                    <li key={p.path}>
                      <QrCode text={`${window.location.origin}${p.path}`} />
                      <p>
                        <strong>{p.label}</strong>
                        <span>{p.path === "/" ? window.location.host : p.path.replace(/\/$/, "")}</span>
                      </p>
                    </li>
                  ))}
                </ul>
                <p className="share-notice">{SHARE.notice}</p>
              </div>
            </Slide>
          )}
        </div>
      </div>

      <nav className="deck-controls" aria-label="Slides">
        <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => move("previous")} disabled={index === 0} aria-label="Previous slide">
          <Chevron direction="left" />
        </button>
        <span className="deck-count">
          {index + 1} / {COUNT}
        </span>
        <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => move("next")} disabled={index === COUNT - 1} aria-label="Next slide">
          <Chevron direction="right" />
        </button>
        {fullscreen.available && <span className="deck-divider" />}
        {fullscreen.available && (
          <button
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={fullscreen.toggle}
            aria-label={fullscreen.on ? "Leave full screen" : "Full screen"}
            title={fullscreen.on ? "Leave full screen (F)" : "Full screen (F)"}
          >
            <FullscreenIcon on={fullscreen.on} />
          </button>
        )}
      </nav>
      <div className="deck-progress" style={{ width: `${(100 * (index + 1)) / COUNT}%` }} />
      <p className="visually-hidden" aria-live="polite">
        Slide {index + 1} of {COUNT}: {TITLES[index]}
      </p>
    </main>
  );
}

function Slide({ at, index, className, children }: { at: number; index: number; className: string; children: ReactNode }) {
  const current = at === index;
  return (
    <section
      className={`slide ${className}${current ? " current" : ""}`}
      aria-roledescription="slide"
      aria-label={`${at + 1} of ${COUNT}`}
      aria-hidden={!current}
    >
      {children}
    </section>
  );
}

function ClipSlide({ clip, number, current, near }: { clip: Clip; number: number; current: boolean; near: boolean }) {
  return (
    <>
      <div className="clip-text">
        <p className="clip-number">{String(number).padStart(2, "0")}</p>
        <h2>{clip.title}</h2>
        {(clip.flood || clip.tags) && (
          <p className="tags">
            {clip.flood && <span className={`tag flood-${clip.flood}`}>{FLOOD_LABEL[clip.flood]}</span>}
            {clip.tags?.map((t) => (
              <span key={t} className="tag">
                {t}
              </span>
            ))}
          </p>
        )}
        <p className="clip-caption">{keepTogether(clip.text)}</p>
      </div>
      <div className="clip-media">
        <div className="clip-frame">
          <ClipImage clip={clip} current={current} near={near} />
        </div>
      </div>
      <p className="slide-footer" aria-hidden="true">
        <img src="/icon.svg" alt="" width={20} height={20} />
        {INTRO.name}
      </p>
    </>
  );
}

/** The text with a number never split from its unit or from the rest of the number ("604 m",
    "132 500") at the end of a line. */
function keepTogether(text: string): string {
  return text.replace(/(\d) (?=\d|c?m\b)/g, "$1\u00a0");
}

// Each clip is fetched once, then shown from a new object URL every time its slide opens, so it plays
// from its first frame instead of wherever the browser's copy of it has got to.
const fetched = new Map<string, Promise<Blob>>();

function fetchClip(url: string): Promise<Blob> {
  let blob = fetched.get(url);
  if (!blob) {
    blob = fetch(url).then((r) => {
      if (!r.ok) throw new Error(`${r.status} for ${url}`);
      return r.blob();
    });
    blob.catch(() => fetched.delete(url));
    fetched.set(url, blob);
  }
  return blob;
}

function ClipImage({ clip, current, near }: { clip: Clip; current: boolean; near: boolean }) {
  const url = clipUrl(clip.name);
  const [src, setSrc] = useState<string>();
  const made = useRef<string>();

  useEffect(() => {
    if (near && url) fetchClip(url).catch(() => undefined);
  }, [near, url]);

  useEffect(() => {
    if (!current || !url) return;
    let stale = false;
    fetchClip(url).then(
      (blob) => {
        if (stale) return;
        const previous = made.current;
        made.current = URL.createObjectURL(blob);
        setSrc(made.current);
        if (previous) URL.revokeObjectURL(previous);
      },
      () => !stale && setSrc(url), // the file itself, from wherever it has got to
    );
    return () => {
      stale = true;
    };
  }, [current, url]);

  useEffect(
    () => () => {
      if (made.current) URL.revokeObjectURL(made.current);
    },
    [],
  );

  if (!src) return null;
  return <img src={src} alt={clip.alt} width={clip.phone ? 340 : 640} height={clip.phone ? 736 : 400} draggable={false} />;
}

function useFullscreen() {
  const available = typeof document !== "undefined" && document.fullscreenEnabled === true;
  const [on, setOn] = useState(false);

  useEffect(() => {
    const onChange = () => setOn(document.fullscreenElement != null);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  const toggle = useCallback(() => {
    if (!available) return;
    const request = document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
    request.catch(() => undefined);
  }, [available]);

  return { available, on, toggle };
}

/** A QR code of the text, drawn as an SVG with the white margin of four modules that scanners need. */
function QrCode({ text }: { text: string }) {
  const { size, d } = useMemo(() => {
    const qr = qrcode(0, "M");
    qr.addData(text);
    qr.make();
    const n = qr.getModuleCount();
    const margin = 4;
    // One rectangle per run of dark modules in a row.
    let d = "";
    for (let row = 0; row < n; row++) {
      for (let col = 0; col < n; col++) {
        if (!qr.isDark(row, col)) continue;
        const start = col;
        while (col + 1 < n && qr.isDark(row, col + 1)) col++;
        d += `M${start + margin} ${row + margin}h${col + 1 - start}v1h${start - col - 1}z`;
      }
    }
    return { size: n + 2 * margin, d };
  }, [text]);

  return (
    <svg className="qr-code" viewBox={`0 0 ${size} ${size}`} shapeRendering="crispEdges" role="img" aria-label={`QR code for ${text}`}>
      <rect width={size} height={size} fill="#fff" />
      <path d={d} fill="#1b2430" />
    </svg>
  );
}

/** Water lines along the foot of the title and QR code slides, like the app's icon. */
function Waves() {
  // Twice the slide's width, so that sliding it along by half loops without a seam.
  const line = (y: number, half: number, rise: number) => {
    let d = `M0 ${y} Q${half / 2} ${y - rise} ${half} ${y}`;
    for (let x = 2 * half; x <= 2880; x += half) d += ` T${x} ${y}`;
    return d;
  };
  return (
    <div className="waves" aria-hidden="true">
      <svg viewBox="0 0 2880 240" preserveAspectRatio="none">
        <path className="wave-fill" d={`${line(176, 240, 22)} V240 H0 Z`} />
        <path d={line(92, 180, 18)} />
        <path d={line(134, 144, 14)} />
        <path d={line(176, 240, 22)} />
      </svg>
    </div>
  );
}

function Chevron({ direction }: { direction: "left" | "right" }) {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
      <path d={direction === "left" ? "M12.5 4.5 7 10l5.5 5.5" : "M7.5 4.5 13 10l-5.5 5.5"} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function FullscreenIcon({ on }: { on: boolean }) {
  const d = on ? "M7 3v4H3M13 3v4h4M7 17v-4H3M13 17v-4h4" : "M3 7V3h4M17 7V3h-4M3 13v4h4M17 13v4h-4";
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true">
      <path d={d} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
