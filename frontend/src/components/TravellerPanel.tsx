import { useId } from "react";
import { cm } from "../format";
import type { Options, Traveller, TravellerInfo } from "../types";

interface Props {
  options: Options;
  traveller: Traveller;
  info: TravellerInfo | null;
  onChange: (t: Traveller) => void;
}

export function TravellerPanel({ options, traveller, info, onChange }: Props) {
  const ids = { height: useId(), wading: useId(), alpha: useId() };
  const set = (patch: Partial<Traveller>) => onChange({ ...traveller, ...patch });
  const heightM = traveller.height_cm / 100;

  return (
    <section className="card" aria-labelledby="you-title">
      <h2 id="you-title">You</h2>
      <div className="row">
        <label htmlFor={ids.height}>Height</label>
        <div className="height">
          <input
            id={ids.height}
            type="number"
            inputMode="numeric"
            min={60}
            max={230}
            step={1}
            value={traveller.height_cm}
            onChange={(e) => {
              const v = Number(e.target.value);
              if (v >= 60 && v <= 230) set({ height_cm: v });
            }}
          />
          <span>cm</span>
        </div>
      </div>
      <div className="row">
        <label htmlFor={ids.wading}>Deepest water you will walk through</label>
        <select
          id={ids.wading}
          value={traveller.wading}
          onChange={(e) => set({ wading: e.target.value })}
          disabled={traveller.wheelchair}
        >
          {options.body_parts.map((p) => (
            <option key={p.key} value={p.key}>
              {p.fraction === null
                ? `${p.label} (${cm(options.dry_depth_m)})`
                : `${p.label} (${cm(Math.min(p.fraction * heightM, options.hard_limit_m))})`}
            </option>
          ))}
        </select>
      </div>
      <label className="check">
        <input type="checkbox" checked={traveller.wheelchair} onChange={(e) => set({ wheelchair: e.target.checked })} />
        I use a wheelchair or mobility aid
      </label>
      {info && (
        <p className="limit">
          Your limit: <strong>{cm(info.depth_limit_m)}</strong>{" "}
          <span className="muted">(never more than {cm(options.hard_limit_m)})</span>
        </p>
      )}

      <fieldset className="prefs">
        <legend>Route preference</legend>
        {options.preferences.map((p) => (
          <label key={p.key} className={`pref ${traveller.preference === p.key && traveller.alpha === null ? "pref-on" : ""}`}>
            <input
              type="radio"
              name="preference"
              value={p.key}
              checked={traveller.preference === p.key && traveller.alpha === null}
              onChange={() => set({ preference: p.key, alpha: null })}
            />
            <span>
              <strong>{p.label}</strong>
              <small>{p.summary}</small>
            </span>
          </label>
        ))}
      </fieldset>
      {info && <p className="explain">{info.explanation}</p>}
      <p className="muted small">Water deeper than your limit is always avoided; this only decides whether water within it is worth walking around.</p>
      <details>
        <summary>Advanced</summary>
        <label htmlFor={ids.alpha} className="row-inline">
          Risk weight α: <strong>{(traveller.alpha ?? info?.alpha ?? 2).toFixed(1)}</strong>
        </label>
        <input
          id={ids.alpha}
          type="range"
          min={0}
          max={20}
          step={0.5}
          value={traveller.alpha ?? info?.alpha ?? 2}
          onChange={(e) => set({ alpha: Number(e.target.value) })}
        />
        <p className="muted small">Extra metres worth walking to avoid one metre of water right at your limit.</p>
        {traveller.alpha !== null && (
          <button type="button" className="link" onClick={() => set({ alpha: null })}>
            Back to the preference
          </button>
        )}
      </details>
    </section>
  );
}
