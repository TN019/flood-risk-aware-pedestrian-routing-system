import { cm } from "../format";
import type { FloodLevel, Options, ScenarioSummary } from "../types";

interface Props {
  scenarios: ScenarioSummary[];
  selected: ScenarioSummary | null;
  options: Options;
  onSelect: (id: string) => void;
}

function band(level: FloodLevel): string {
  const low = Math.round(level.lower_m * 100);
  return level.upper_m === null ? `over ${low} cm` : `${low}–${Math.round(level.upper_m * 100)} cm`;
}

export function ConditionsPanel({ scenarios, selected, options, onSelect }: Props) {
  const height = Math.round(options.reference_height_m * 100);
  return (
    <section className="card" aria-labelledby="conditions-title">
      <h2 id="conditions-title">Flood conditions</h2>
      <div className="levels" role="radiogroup" aria-label="Flood scenario">
        {scenarios.map((s) => (
          <button
            key={s.id}
            type="button"
            role="radio"
            aria-checked={selected?.id === s.id}
            className={`level level-${s.level?.key ?? "none"} ${selected?.id === s.id ? "level-on" : ""}`}
            onClick={() => onSelect(s.id)}
          >
            {s.level ? s.level.label : "None"}
          </button>
        ))}
      </div>
      {selected && (
        <div className="level-card">
          <p className="level-title">{selected.title}</p>
          {selected.level && selected.typical_depth_m !== null ? (
            <p>
              Water {selected.level.body_range} ({band(selected.level)} for a {height} cm adult). Typical depth on
              flooded footpaths here: <strong>{cm(selected.typical_depth_m)}</strong>.
            </p>
          ) : (
            <p>No standing water.</p>
          )}
          <p className="muted">{selected.description}</p>
          {selected.sources.length > 0 && (
            <details>
              <summary>Sources</summary>
              <ul className="sources">
                {selected.sources.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </section>
  );
}
