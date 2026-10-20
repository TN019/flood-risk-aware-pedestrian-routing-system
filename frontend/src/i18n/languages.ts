// The languages the web client offers, and which one a visitor sees. Kept free of React so it can
// be tested on its own. Why these five: /reference (Languages) and docs/languages.md.

export const LANGUAGES = [
  { code: "en", name: "English" },
  { code: "es", name: "Español" },
  { code: "zh-Hans", name: "中文（简体）" },
  { code: "hi", name: "हिन्दी" },
  { code: "ko", name: "한국어" },
] as const;

export type Lang = (typeof LANGUAGES)[number]["code"];

export const DEFAULT_LANG: Lang = "en";

// Shared by the app, /reference and /benchmark, which are served from the same origin.
const STORAGE_KEY = "floodroute.language";

/** The offered language a BCP 47 tag asks for, if any: "es-AR" is Spanish, and every Chinese tag
 * is Chinese in its one offered written form, Simplified. */
export function offered(tag: string | null | undefined): Lang | null {
  if (!tag) return null;
  if (LANGUAGES.some((l) => l.code === tag)) return tag as Lang;
  const primary = tag.trim().split(/[-_]/)[0].toLowerCase();
  if (primary === "zh") return "zh-Hans";
  return LANGUAGES.find((l) => l.code === primary)?.code ?? null;
}

/** The language to show: the visitor's earlier choice, else the first offered language their
 * browser asks for, else English. */
export function chooseLang(stored: string | null, browser: readonly string[]): Lang {
  return offered(stored) ?? browser.map(offered).find((l): l is Lang => l !== null) ?? DEFAULT_LANG;
}

/** The visitor's earlier choice. Storage may be unavailable (private windows, blocked cookies):
 * the pages then follow the browser's language. */
export function storedLang(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function storeLang(lang: Lang): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    // the choice then lasts until the page is closed
  }
}

export function browserLangs(): readonly string[] {
  return typeof navigator === "undefined" ? [] : navigator.languages?.length ? navigator.languages : [navigator.language];
}
