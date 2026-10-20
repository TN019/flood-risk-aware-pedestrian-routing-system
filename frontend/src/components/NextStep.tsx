import { cm, depthSummary, distance, gradientPercent, hasGradients, minutes } from "../format";
import { detourText, route, situation, whyNoRoute } from "../guidance";
import { useI18n } from "../i18n/I18n";
import type { Translate } from "../i18n/translate";
import type { RouteKind } from "../routeStyles";
import type { Options, RouteJson, TripPlan } from "../types";
import { RouteSwatch } from "./Swatch";

interface Props {
  trip: TripPlan;
  options: Options;
  selected: RouteKind | null;
  onSelect: (kind: RouteKind | null) => void;
  onUseLimit: (downgrade: NonNullable<TripPlan["downgrade"]>) => void;
}

function Metrics({ r, options }: { r: RouteJson; options: Options }) {
  const { t } = useI18n();
  const m = r.metrics;
  const wet = m.max_depth_m !== null && m.max_depth_m > options.dry_depth_m;
  return (
    <div className="metrics">
      <div>
        <span className="metric-value">{distance(m.length_m)}</span>
        <span className="metric-label">
          {t("metric.walk")}
          {m.detour_ratio && m.detour_ratio > 0.005 ? ` · ${t("metric.vsShortest", { percent: Math.round(m.detour_ratio * 100) })}` : ""}
        </span>
      </div>
      <div>
        <span className="metric-value">{minutes(m.travel_time_s, t)}</span>
        <span className="metric-label">{t("metric.estimated")}</span>
      </div>
      <div>
        <span className="metric-value">{m.max_depth_m === null ? t("metric.unknown") : wet ? cm(m.max_depth_m) : t("metric.dry")}</span>
        <span className="metric-label">{wet ? m.max_depth_label : t("metric.deepest")}</span>
      </div>
      <div>
        <span className="metric-value">{distance(m.wading_length_m)}</span>
        <span className="metric-label">{t("metric.inWater")}</span>
      </div>
      {hasGradients(r) ? (
        <>
          <div>
            <span className="metric-value">{gradientPercent(r.max_gradient)}</span>
            <span className="metric-label">{t("metric.steepest")}</span>
          </div>
          <div>
            <span className="metric-value">{gradientPercent(r.min_gradient)}</span>
            <span className="metric-label">{t("metric.gentlest")}</span>
          </div>
        </>
      ) : (
        <div>
          <span className="metric-value">—</span>
          <span className="metric-label">{t("metric.noGradient")}</span>
        </div>
      )}
    </div>
  );
}

interface ChoiceProps {
  kind: RouteKind | null; // null: nothing to show on the map
  selected: RouteKind | null;
  onSelect: (kind: RouteKind | null) => void;
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}

/** One way forward. Selecting it highlights its route on the map. */
function Choice({ kind, selected, onSelect, title, children, action }: ChoiceProps) {
  const { t } = useI18n();
  const on = kind !== null && selected === kind;
  return (
    <div className={`choice ${on ? "choice-on" : ""}`}>
      <button
        type="button"
        className="choice-main"
        aria-pressed={kind === null ? undefined : on}
        disabled={kind === null}
        onClick={() => kind && onSelect(on ? null : kind)}
      >
        <span className="choice-title">
          {kind && <RouteSwatch kind={kind} />}
          {title}
        </span>
        {children && <span className="choice-body">{children}</span>}
        {kind && <span className="choice-hint">{on ? t("next.shown") : t("next.show")}</span>}
      </button>
      {action}
    </div>
  );
}

function routeLine(r: RouteJson, options: Options, t: Translate): string {
  const m = r.metrics;
  return t("next.routeLine", {
    distance: distance(m.length_m),
    time: minutes(m.travel_time_s, t),
    depth: depthSummary(m.max_depth_m, m.max_depth_label, options.dry_depth_m, t),
  });
}

export function NextStep({ trip, options, selected, onSelect, onUseLimit }: Props) {
  const { t } = useI18n();
  const sit = situation(trip);
  const why = whyNoRoute(trip, t);
  const d = trip.downgrade;
  const r = trip.refuge;
  const least = trip.least_water;

  const downgradeChoice = d && (
    <Choice
      kind="downgrade"
      selected={selected}
      onSelect={onSelect}
      title={t("next.accept", { water: d.water, depth: cm(d.depth_limit_m) })}
      action={
        <button type="button" className="button" onClick={() => onUseLimit(d)}>
          {t("next.useLimit")}
        </button>
      }
    >
      {routeLine(d.route, options, t)}
    </Choice>
  );
  const refugeChoice = r && (
    <Choice kind="refuge" selected={selected} onSelect={onSelect} title={t("next.refuge", { name: r.name })}>
      {t("next.refugeWay", { entrance: r.entrance_label, route: routeLine(r.route, options, t) })}
      {!r.within_limit && <span className="warn-text"> {t("next.refugeOverLimit")}</span>}
    </Choice>
  );
  const stayChoice = (
    <Choice kind={null} selected={selected} onSelect={onSelect} title={t("next.stayInside", { place: trip.start.label })}>
      {t("next.wait")}
    </Choice>
  );
  const leastChoice = least && (
    <Choice kind="least_water" selected={selected} onSelect={onSelect} title={t("next.leastWater")}>
      {routeLine(least.route, options, t)}
    </Choice>
  );

  let headline: string;
  let body: React.ReactNode = null;
  switch (sit) {
    case "go":
      headline = t("next.go");
      body = <Metrics r={route(trip, "recommended")!} options={options} />;
      break;
    case "detour":
      headline = t("next.detour");
      body = (
        <>
          <p>{detourText(trip, t)}</p>
          <Metrics r={route(trip, "recommended")!} options={options} />
        </>
      );
      break;
    case "choose":
      headline = t("next.choose");
      body = (
        <div className="choices-pair">
          {downgradeChoice}
          {r ? refugeChoice : stayChoice}
        </div>
      );
      break;
    case "downgrade":
      headline = t("next.downgrade");
      body = downgradeChoice;
      break;
    case "shelter":
      if (trip.origin.level === "critical") {
        headline = t("next.shelterCritical");
        body = (
          <details className="fold">
            <summary>{t("next.shelterFold")}</summary>
            {refugeChoice}
          </details>
        );
      } else {
        headline = t("next.shelter");
        body = refugeChoice;
      }
      break;
    case "stay":
      headline = t("next.stay", { place: trip.start.label });
      body = leastChoice;
      break;
    case "help":
      headline = t("next.help");
      body = (
        <>
          <p>{t("next.helpBody")}</p>
          {leastChoice}
        </>
      );
      break;
    default:
      headline = t("next.unreachable");
  }

  return (
    <section className={`card next next-${sit}`} aria-labelledby="next-title" aria-live="polite">
      <p className="next-label">{t("next.label")}</p>
      <h2 id="next-title">{headline}</h2>
      {why && sit !== "go" && sit !== "detour" && <p className="why">{why}</p>}
      {body}
    </section>
  );
}
