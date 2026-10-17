import { useEffect, useState } from "react";
import { cm, depthSummary, distance, minutes } from "../format";
import type { RouteKind } from "../routeStyles";
import type { Options, TripPlan } from "../types";
import { NextStep } from "./NextStep";
import { RouteSwatch } from "./Swatch";

interface Props {
  trip: TripPlan;
  options: Options;
  sosSentAt: number | null;
  onSos: (sentAt: number | null) => void;
  onUseLimit: (downgrade: NonNullable<TripPlan["downgrade"]>) => void;
  selected: RouteKind | null;
  onSelect: (kind: RouteKind | null) => void;
}

function OriginAlert({ trip }: { trip: TripPlan }) {
  const o = trip.origin;
  const depth = o.depth_m === null ? "water of unknown depth" : `${cm(o.depth_m)} of water`;
  const here = o.depth_m === null ? "unknown" : cm(o.depth_m);
  switch (o.level) {
    case "over_limit":
      return <div className="alert alert-warn" role="alert">You are standing in {depth} ({o.depth_label}), deeper than your limit.</div>;
    case "deep":
      return <div className="alert alert-warn" role="alert">⚠️ You are standing in {depth} ({o.depth_label}). Move carefully; help is available.</div>;
    case "very_deep":
      return <div className="alert alert-orange" role="alert">🟠 The water here is {here} deep, above your knee. Calling for help is recommended before moving.</div>;
    case "critical":
      return (
        <div className="alert alert-red" role="alert">
          🔴 {o.depth_m === null ? "The depth here is unknown." : `The water here is ${here} deep (${o.depth_label}).`} Stay where you are if
          you can and call for help now.
        </div>
      );
    default:
      return null;
  }
}

function Emergency({ trip, options, sosSentAt, onSos }: Pick<Props, "trip" | "options" | "sosSentAt" | "onSos">) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (sosSentAt === null) return;
    const timer = window.setInterval(() => setNow(Date.now()), 500);
    return () => window.clearInterval(timer);
  }, [sosSentAt]);
  if (!trip.emergency) return null;
  const { advice, sos } = trip.emergency;
  const only = advice === "only option";
  const elapsed = sosSentAt === null ? 0 : Math.max(0, (now - sosSentAt) / 1000);
  const depth = sos.depth_m === null ? "unknown" : cm(sos.depth_m);
  return (
    <section className={`card emergency ${advice === "available" ? "" : "emergency-urgent"}`} aria-labelledby="emergency-title">
      <h2 id="emergency-title">Emergency help — {only ? "your only option" : advice}</h2>
      <div className="emergency-actions">
        <a className="button button-danger" href="tel:000">
          📞 Call 000
        </a>
        {sosSentAt === null ? (
          <button type="button" className="button" onClick={() => onSos(Date.now())}>
            📣 Alert people nearby (SOS)
          </button>
        ) : (
          <div className="sos-sent" role="status">
            <span>
              SOS sent {Math.round(elapsed)} s ago with your location and {depth} water depth (simulated).
            </span>
            {elapsed < options.sos_undo_seconds && (
              <button type="button" className="link" onClick={() => onSos(null)}>
                Undo ({Math.ceil(options.sos_undo_seconds - elapsed)} s)
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

/** Every route that was planned, each selectable to see it on the map. */
function Comparison({ trip, options, selected, onSelect }: Pick<Props, "trip" | "options" | "selected" | "onSelect">) {
  const routes = trip.routes!;
  return (
    <section className="card" aria-labelledby="compare-title">
      <h2 id="compare-title">Compare routes</h2>
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
                    {o.name}
                    {unsafe && <span className="tag-unsafe">not safe</span>}
                  </span>
                </span>
                {m ? (
                  <span className="compare-values">
                    <span>
                      {distance(m.length_m)} · {minutes(m.travel_time_s)}
                      {m.detour_ratio && m.detour_ratio > 0.005 ? ` (+${Math.round(m.detour_ratio * 100)}%)` : ""}
                    </span>
                    <span>
                      Deepest {depthSummary(m.max_depth_m, m.max_depth_label, options.dry_depth_m)} · {distance(m.wading_length_m)} in water
                    </span>
                    {unsafe && <span className="warn-text">{m.segments_over_limit} section(s) over your limit</span>}
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
        Select a route to see it on the map. {routes.blocked_edges} network sections are over your limit in this scenario.
        {routes.steps_avoided ? " Every route avoids the steps on the shortest way." : routes.step_free ? " Every route is step-free." : ""}
      </p>
    </section>
  );
}

export function TripResults(props: Props) {
  const { trip, options } = props;
  const recommended = trip.routes?.options.find((o) => o.kind === "recommended")?.route ?? null;
  const place = (p: TripPlan["start"], label: string | null | undefined) =>
    p.method === "point" ? "the selected point" : `${p.label}${label ? ` (${label})` : ""}`;
  return (
    <div className="results">
      <OriginAlert trip={trip} />
      <Emergency {...props} />
      <NextStep trip={trip} options={options} selected={props.selected} onSelect={props.onSelect} onUseLimit={props.onUseLimit} />
      {trip.routes && <Comparison trip={trip} options={options} selected={props.selected} onSelect={props.onSelect} />}
      {recommended && (
        <p className="muted small">
          From {place(trip.start, recommended.from.label)} to {place(trip.destination, recommended.to.label)}.
        </p>
      )}
    </div>
  );
}
