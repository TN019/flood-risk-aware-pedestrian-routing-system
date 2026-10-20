import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { en, type Messages } from "./messages/en";
import { browserLangs, chooseLang, DEFAULT_LANG, type Lang, LANGUAGES, storedLang, storeLang } from "./languages";
import { english, fillRich, pluralForm, type Translate, translator, type Values } from "./translate";
import type { MessageKey } from "./messages/en";

// English ships with every page; each other catalogue is loaded only when it is chosen.
const LOADERS: Record<Exclude<Lang, "en">, () => Promise<{ default: Messages }>> = {
  es: () => import("./messages/es"),
  "zh-Hans": () => import("./messages/zh-Hans"),
  hi: () => import("./messages/hi"),
  ko: () => import("./messages/ko"),
};

async function load(lang: Lang): Promise<Messages> {
  return lang === "en" ? en : (await LOADERS[lang]()).default;
}

export interface Loaded {
  lang: Lang;
  messages: Messages;
}

/** The visitor's language and its catalogue, before the page is drawn, so it never shows English
 * first. English if the catalogue cannot be loaded. */
export async function startI18n(): Promise<Loaded> {
  const lang = chooseLang(storedLang(), browserLangs());
  document.documentElement.lang = lang;
  try {
    return { lang, messages: await load(lang) };
  } catch {
    document.documentElement.lang = DEFAULT_LANG;
    return { lang: DEFAULT_LANG, messages: en };
  }
}

interface I18n {
  lang: Lang;
  t: Translate;
  /** A sentence whose placeholders hold elements as well as text. */
  rich: (key: MessageKey, values: Record<string, ReactNode>) => ReactNode[];
  /** The "one" or "other" form of `${key}.one` / `${key}.other` for a count. */
  plural: (key: string, count: number, values?: Values) => string;
  setLang: (lang: Lang) => void;
}

const Context = createContext<I18n>({
  lang: DEFAULT_LANG,
  t: english,
  rich: (key, values) => fillRich(en[key], values),
  plural: (key, count, values) => english(`${key}.${pluralForm(DEFAULT_LANG, count)}` as MessageKey, { count, ...values }),
  setLang: () => undefined,
});

export function I18nProvider({ initial, children }: { initial: Loaded; children: ReactNode }) {
  const [current, setCurrent] = useState<Loaded>(initial);

  const setLang = useCallback((lang: Lang) => {
    storeLang(lang);
    load(lang)
      .then((messages) => setCurrent({ lang, messages }))
      .catch(() => undefined); // offline: keep the language shown
  }, []);

  useEffect(() => {
    document.documentElement.lang = current.lang;
  }, [current.lang]);

  const value = useMemo<I18n>(() => {
    const { lang, messages } = current;
    const t = translator(messages);
    return {
      lang,
      t,
      rich: (key, values) => fillRich(messages[key] ?? en[key], values),
      plural: (key, count, values) => t(`${key}.${pluralForm(lang, count)}` as MessageKey, { count, ...values }),
      setLang,
    };
  }, [current, setLang]);

  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useI18n(): I18n {
  return useContext(Context);
}

/** The page's title in the tab, in the visitor's language. */
export function useDocumentTitle(key: MessageKey, values?: Values) {
  const { t } = useI18n();
  const title = t(key, values);
  useEffect(() => {
    document.title = title;
  }, [title]);
}

/** Choosing the language, with each language named in its own script. */
export function LanguageSwitcher() {
  const { lang, t, setLang } = useI18n();
  return (
    <label className="lang-switch" title={t("language.label")}>
      <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
        <circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" strokeWidth="1.3" />
        <path d="M1.5 8h13M8 1.5c2 2.2 2 10.8 0 13M8 1.5c-2 2.2-2 10.8 0 13" fill="none" stroke="currentColor" strokeWidth="1.3" />
      </svg>
      <select value={lang} onChange={(e) => setLang(e.target.value as Lang)} aria-label={t("language.label")}>
        {LANGUAGES.map((l) => (
          <option key={l.code} value={l.code} lang={l.code}>
            {l.name}
          </option>
        ))}
      </select>
    </label>
  );
}
