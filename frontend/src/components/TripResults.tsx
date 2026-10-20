import { accessNote, cm, depthSummary, distance, gradientSummary, minutes } from "../format";
import { useI18n } from "../i18n/I18n";
import type { RouteKind } from "../routeStyles";
import type { Options, TripPlan } from "../types";
import { NextStep } from "./NextStep";
import { SosControl, type SosState } from "./Sos";
import { RouteSwatch } from "./Swatch";

interface Props {
  trip: TripPlan;
  options: Options;
  sos: SosState | null;
  onSos: (sos: SosState | null) => void;
  onUseLimit: (downgrade: NonNullable<TripPlan["downgrade"]>) => void;
  selected: RouteKind | null;
  onSelect: (kind: RouteKind | null) => void;
}

const ADVICE = {
  available: "emergency.available",
  recommended: "emergency.recommended",
  "strongly recommended": "emergency.stronglyRecommended",
  "only option": "emergency.onlyOption",
} as const;

function OriginAlert({ trip }: { trip: TripPlan }) {
  const { t } = useI18n();
  const o = trip.origin;
  const water = o.depth_m === null ? t("origin.unknownWater") : t("origin.water", { depth: cm(o.depth_m) });
  const here = o.depth_m === null ? t("depth.unknown") : cm(o.depth_m);
  switch (o.level) {
    case "over_limit":
      return <div className="alert alert-warn" role="alert">{t("origin.overLimit", { water, label: o.depth_label })}</div>;
    case "deep":
      return <div className="alert alert-warn" role="alert">⚠️ {t("origin.deep", { water, label: o.depth_label })}</div>;
    case "very_deep":
      return <div className="alert alert-orange" role="alert">🟠 {t("origin.veryDeep", { depth: here })}</div>;
    case "critical":
      return (
        <div className="alert alert-red" role="alert">
          🔴 {o.depth_m === null ? t("origin.criticalUnknown") : t("origin.critical", { depth: here, label: o.depth_label })}{" "}
          {t("origin.criticalAction")}
        </div>
      );
    default:
      return null;
  }
}

function Emergency({ trip, options, sos, onSos }: Pick<Props, "trip" | "options" | "sos" | "onSos">) {
  const { t } = useI18n();
  if (!trip.emergency) return null;
  const { advice, reason, sos: request } = trip.emergency;
  return (
    <section className={`card emergency ${advice === "available" ? "" : "emergency-urgent"}`} aria-labelledby="emergency-title">
      <h2 id="emergency-title">{t("emergency.title", { advice: t(ADVICE[advice]) })}</h2>
      {reason === "cut_off" && <p className="emergency-why">{t("emergency.cutOff")}</p>}
      <div className="emergency-actions">
        <a className="button button-danger" href="tel:000">
          📞 {t("help.call000")}
        </a>
        <a className="button" href="tel:132500">
          📞 VICSES 132 500
        </a>
        <SosControl
          sos={sos}
          shared={{ place: "here", depth: request.depth_m === null ? null : cm(request.depth_m) }}
          undoSeconds={options.sos_undo_seconds}
          onSos={onSos}
        />
      </div>
      <p className="small muted">{t("emergency.note")}</p>
    </section>
  );
}

/** Every route that was planned, each selectable to see it on the map. */
function Comparison({ trip, options, selected, onSelect }: Pick<Props, "trip" | "options" | "selected" | "onSelect">) {
  const { t } = useI18n();
  const routes = trip.routes!;
  const note = accessNote(routes, t);
  return (
    <section className="card" aria-labelledby="compare-title">
      <h2 id="compare-title">{t("compare.title")}</h2>
      <ul className="compare">
        {routes.options.map((o) => {
          const m = o.route?.metrics;
          const unsafe = !!m && m.segments_over_limit > 0;
          const on = selected === o.kind;
          return (
            <li key={o.kind}>
              <button
                type="button"
                className={`compare-row ${on ? "compare-on" : ""}`}
                disabled={!o.route}
                aria-pressed={o.route ? on : undefined}
                onClick={() => onSelect(on ? null : o.kind)}
              >
                <span className="compare-name">
                  <RouteSwatch kind={o.kind} />
                  <span>
                    {t(`route.${o.kind}`)}
                    {unsafe && <span className="tag-unsafe">{t("compare.notSafe")}</span>}
                  </span>
                </span>
                {m ? (
                  <span className="compare-values">
                    <span>
                      {distance(m.length_m)} · {minutes(m.travel_time_s, t)}
                      {m.detour_ratio && m.detour_ratio > 0.005 ? ` (+${Math.round(m.detour_ratio * 100)}%)` : ""}
                    </span>
                    <span>
                      {t("compare.deepest", {
                        depth: depthSummary(m.max_depth_m, m.max_depth_label, options.dry_depth_m, t),
                        water: distance(m.wading_length_m),
                      })}
                    </span>
                    <span>{gradientSummary(o.route!, t)}</span>
                    {unsafe && <span className="warn-text">{t("compare.overLimit", { count: m.segments_over_limit })}</span>}
                  </span>
                ) : (
                  <span className="compare-values warn-text">{o.error}</span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
      <p className="muted small">
        {t("compare.hint")} {t("compare.blocked", { count: routes.blocked_edges })}
        {note && ` ${note}`}
      </p>
    </section>
  );
}

export function TripResults(props: Props) {
  const { t } = useI18n();
  const { trip, options } = props;
  const recommended = trip.routes?.options.find((o) => o.kind === "recommended")?.route ?? null;
  const place = (p: TripPlan["start"], access: string | null | undefined) =>
    p.method === "point" ? t("trip.selectedPoint") : access ? t("trip.placeAccess", { place: p.label, access }) : p.label;
  return (
    <div className="results">
      <OriginAlert trip={trip} />
      <Emergency {...props} />
      <NextStep trip={trip} options={options} selected={props.selected} onSelect={props.onSelect} onUseLimit={props.onUseLimit} />
      {trip.routes && <Comparison trip={trip} options={options} selected={props.selected} onSelect={props.onSelect} />}
      {recommended && (
        <p className="muted small">
          {t("trip.fromTo", { from: place(trip.start, recommended.from.label), to: place(trip.destination, recommended.to.label) })}
        </p>
      )}
    </div>
  );
}
