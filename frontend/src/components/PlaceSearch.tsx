import { type FormEvent, useId, useState } from "react";
import { api, errorText } from "../api";
import { useI18n } from "../i18n/I18n";
import type { MessageKey } from "../i18n/messages/en";
import type { Translate } from "../i18n/translate";
import type { ChosenPoint, SearchHit } from "../types";

interface Props {
  label: string;
  value: ChosenPoint | null;
  active: boolean; // the next map click sets this point
  onActivate: () => void;
  onPick: (hit: SearchHit) => void;
  onClear: () => void;
  extra?: React.ReactNode;
}

function describe(p: ChosenPoint, t: Translate): string {
  if (p.label) return p.label;
  const place = p.source === "location" ? t("trip.yourLocation") : t("trip.pointOnMap");
  return t("trip.pointAt", { place, lat: p.lat.toFixed(5), lon: p.lon.toFixed(5) });
}

export function PlaceSearch({ label, value, active, onActivate, onPick, onClear, extra }: Props) {
  const { lang, t } = useI18n();
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [busy, setBusy] = useState(false);
  // The service's own message, or one of ours (a key, so it follows a change of language).
  const [error, setError] = useState<{ text: string } | { key: MessageKey } | null>(null);
  const inputId = useId();

  async function search(e: FormEvent) {
    e.preventDefault();
    if (query.trim().length < 3) {
      setError({ key: "search.tooShort" });
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setHits(await api.search(query, lang));
    } catch (err) {
      setHits(null);
      setError({ text: errorText(err, t, t("search.failed")) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`place ${active ? "place-active" : ""}`}>
      <div className="place-head">
        <label htmlFor={inputId}>{label}</label>
        <button type="button" className={`chip ${active ? "chip-on" : ""}`} onClick={onActivate} aria-pressed={active}>
          {active ? t("search.onMapActive") : t("search.onMap")}
        </button>
      </div>
      {value ? (
        <div className="place-value">
          <span>{describe(value, t)}</span>
          <button type="button" className="link" onClick={onClear}>
            {t("search.change")}
          </button>
        </div>
      ) : (
        <>
          <form className="search" onSubmit={search} role="search">
            <input
              id={inputId}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("search.placeholder")}
              autoComplete="off"
              enterKeyHint="search"
            />
            <button type="submit" disabled={busy}>
              {busy ? "…" : t("search.button")}
            </button>
          </form>
          {extra}
          {error && <p className="hint error-text">{"key" in error ? t(error.key) : error.text}</p>}
          {hits && hits.length === 0 && <p className="hint">{t("search.noMatch")}</p>}
          {hits && hits.length > 0 && (
            <ul className="hits">
              {hits.map((hit) => (
                <li key={`${hit.lat},${hit.lon}`}>
                  <button
                    type="button"
                    onClick={() => {
                      onPick(hit);
                      setHits(null);
                      setQuery("");
                    }}
                  >
                    <strong>{hit.label.split(",")[0]}</strong>
                    <span>{hit.label.split(",").slice(1, 3).join(",")}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
