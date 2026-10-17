import { cm, depthSummary, distance, minutes } from "../format";
import { acceptText, detourText, route, situation, whyNoRoute } from "../guidance";
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
  const m = r.metrics;
  const wet = m.max_depth_m !== null && m.max_depth_m > options.dry_depth_m;
  return (
    <div className="metrics">
      <div>
        <span className="metric-value">{distance(m.length_m)}</span>
        <span className="metric-label">
          walk{m.detour_ratio && m.detour_ratio > 0.005 ? ` · +${Math.round(m.detour_ratio * 100)}% vs shortest` : ""}
        </span>
      </div>
      <div>
        <span className="metric-value">{minutes(m.travel_time_s)}</span>
        <span className="metric-label">estimated</span>
      </div>
      <div>
        <span className="metric-value">{m.max_depth_m === null ? "Unknown" : wet ? cm(m.max_depth_m) : "Dry"}</span>
        <span className="metric-label">{wet ? m.max_depth_label : "deepest water"}</span>
      </div>
      <div>
        <span className="metric-value">{distance(m.wading_length_m)}</span>
        <span className="metric-label">in water</span>
      </div>
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
        {kind && <span className="choice-hint">{on ? "Shown on the map" : "Show on the map"}</span>}
      </button>
      {action}
    </div>
  );
}

function routeLine(r: RouteJson, options: Options): string {
  const m = r.metrics;
  return `${distance(m.length_m)} · ${minutes(m.travel_time_s)} · deepest ${depthSummary(m.max_depth_m, m.max_depth_label, options.dry_depth_m)}`;
}

export function NextStep({ trip, options, selected, onSelect, onUseLimit }: Props) {
  const sit = situation(trip);
  const why = whyNoRoute(trip);
  const d = trip.downgrade;
  const r = trip.refuge;
  const least = trip.least_water;

  const downgradeChoice = d && (
    <Choice
      kind="downgrade"
      selected={selected}
      onSelect={onSelect}
      title={`Accept ${acceptText(d)} (${cm(d.depth_limit_m)})`}
      action={
        <button type="button" className="button" onClick={() => onUseLimit(d)}>
          Use this limit
        </button>
      }
    >
      {routeLine(d.route, options)}
    </Choice>
  );
  const refugeChoice = r && (
    <Choice kind="refuge" selected={selected} onSelect={onSelect} title={`Wait at a shelter: ${r.name}`}>
      To the {r.entrance_label}: {routeLine(r.route, options)}. Wait there until the water goes down.
      {!r.within_limit && <span className="warn-text"> The way there crosses water deeper than your limit; it is the shallowest way out.</span>}
    </Choice>
  );
  const stayChoice = (
    <Choice kind={null} selected={selected} onSelect={onSelect} title={`Stay inside ${trip.start.label}`}>
      Wait until the water goes down.
    </Choice>
  );
  const leastChoice = least && (
    <Choice kind="least_water" selected={selected} onSelect={onSelect} title="The way with the least water">
      {routeLine(least.route, options)}
    </Choice>
  );

  let headline: string;
  let body: React.ReactNode = null;
  switch (sit) {
    case "go":
      headline = "You can go: this route stays within your limit";
      body = <Metrics r={route(trip, "recommended")!} options={options} />;
      break;
    case "detour":
      headline = "Take the recommended route";
      body = (
        <>
          <p>{detourText(trip)}</p>
          <Metrics r={route(trip, "recommended")!} options={options} />
        </>
      );
      break;
    case "choose":
      headline = "No route keeps you within your limit. Choose one:";
      body = (
        <div className="choices-pair">
          {downgradeChoice}
          {r ? refugeChoice : stayChoice}
        </div>
      );
      break;
    case "downgrade":
      headline = "No route keeps you within your limit";
      body = downgradeChoice;
      break;
    case "shelter":
      if (trip.origin.level === "critical") {
        headline = "Stay where you are if you can and call for help";
        body = (
          <details className="fold">
            <summary>If you cannot wait for help: the way to shelter</summary>
            {refugeChoice}
          </details>
        );
      } else {
        headline = "Go to a shelter and wait";
        body = refugeChoice;
      }
      break;
    case "stay":
      headline = `Stay inside ${trip.start.label} until the water goes down`;
      body = leastChoice;
      break;
    case "help":
      headline = "No safe way out from here: call for help";
      body = (
        <>
          <p>No shelter can be reached. Stay on the highest ground you can reach.</p>
          {leastChoice}
        </>
      );
      break;
    default:
      headline = "No route connects these points";
  }

  return (
    <section className={`card next next-${sit}`} aria-labelledby="next-title" aria-live="polite">
      <p className="next-label">Next step</p>
      <h2 id="next-title">{headline}</h2>
      {why && sit !== "go" && sit !== "detour" && <p className="why">{why}</p>}
      {body}
    </section>
  );
}
