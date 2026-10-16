import { type FormEvent, useId, useState } from "react";
import { ApiError, api } from "../api";
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

function describe(p: ChosenPoint): string {
  if (p.label) return p.label;
  const how = p.source === "location" ? "Your location" : "Point on the map";
  return `${how} (${p.lat.toFixed(5)}, ${p.lon.toFixed(5)})`;
}

export function PlaceSearch({ label, value, active, onActivate, onPick, onClear, extra }: Props) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputId = useId();

  async function search(e: FormEvent) {
    e.preventDefault();
    if (query.trim().length < 3) {
      setError("Type at least three letters.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setHits(await api.search(query));
    } catch (err) {
      setHits(null);
      setError(err instanceof ApiError ? err.message : "Search failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`place ${active ? "place-active" : ""}`}>
      <div className="place-head">
        <label htmlFor={inputId}>{label}</label>
        <button type="button" className={`chip ${active ? "chip-on" : ""}`} onClick={onActivate} aria-pressed={active}>
          {active ? "Next map click sets this" : "Set on map"}
        </button>
      </div>
      {value ? (
        <div className="place-value">
          <span>{describe(value)}</span>
          <button type="button" className="link" onClick={onClear}>
            Change
          </button>
        </div>
      ) : (
        <>
          <form className="search" onSubmit={search} role="search">
            <input
              id={inputId}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Eureka Tower, 1 City Road"
              autoComplete="off"
              enterKeyHint="search"
            />
            <button type="submit" disabled={busy}>
              {busy ? "…" : "Search"}
            </button>
          </form>
          {extra}
          {error && <p className="hint error-text">{error}</p>}
          {hits && hits.length === 0 && <p className="hint">No match inside Southbank. Try another name, or click the map.</p>}
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
