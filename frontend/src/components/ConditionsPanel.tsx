import { cm } from "../format";
import { useI18n } from "../i18n/I18n";
import type { Translate } from "../i18n/translate";
import type { FloodLevel, Options, ScenarioSummary } from "../types";

interface Props {
  scenarios: ScenarioSummary[];
  selected: ScenarioSummary | null;
  options: Options;
  onSelect: (id: string) => void;
}

function band(level: FloodLevel, t: Translate): string {
  const low = Math.round(level.lower_m * 100);
  return level.upper_m === null ? t("conditions.over", { depth: `${low} cm` }) : `${low}–${Math.round(level.upper_m * 100)} cm`;
}

export function ConditionsPanel({ scenarios, selected, options, onSelect }: Props) {
  const { t, rich } = useI18n();
  const height = Math.round(options.reference_height_m * 100);
  return (
    <section className="card" aria-labelledby="conditions-title">
      <h2 id="conditions-title">{t("conditions.title")}</h2>
      <div className="levels" role="radiogroup" aria-label={t("conditions.group")}>
        {scenarios.map((s) => (
          <button
            key={s.id}
            type="button"
            role="radio"
            aria-checked={selected?.id === s.id}
            className={`level level-${s.level?.key ?? "none"} ${selected?.id === s.id ? "level-on" : ""}`}
            onClick={() => onSelect(s.id)}
          >
            {s.level ? s.level.label : t("conditions.none")}
          </button>
        ))}
      </div>
      {selected && (
        <div className="level-card">
          <p className="level-title">{selected.title}</p>
          {selected.level && selected.typical_depth_m !== null ? (
            <p>
              {rich("conditions.water", {
                range: selected.level.body_range,
                band: band(selected.level, t),
                height,
                depth: <strong key="depth">{cm(selected.typical_depth_m)}</strong>,
              })}
            </p>
          ) : (
            <p>{t("conditions.dry")}</p>
          )}
          <p className="muted">{selected.description}</p>
          {selected.sources.length > 0 && (
            <details>
              <summary>{t("conditions.sources")}</summary>
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
