import { accessNote, cm, depthSummary, distance, gradientSummary, minutes } from "../format";
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

function Emergency({ trip, options, sos, onSos }: Pick<Props, "trip" | "options" | "sos" | "onSos">) {
  if (!trip.emergency) return null;
  const { advice, reason, sos: request } = trip.emergency;
  const depth = request.depth_m === null ? "" : ` and ${cm(request.depth_m)} water depth`;
  return (
    <section className={`card emergency ${advice === "available" ? "" : "emergency-urgent"}`} aria-labelledby="emergency-title">
      <h2 id="emergency-title">Emergency help — {advice === "only option" ? "your only option" : advice}</h2>
      {reason === "cut_off" && (
        <p className="emergency-why">
          You are cut off by deep water. Stay inside, and move to a higher floor if water comes into the building.
        </p>
      )}
      <div className="emergency-actions">
        <a className="button button-danger" href="tel:000">
          📞 Call 000
        </a>
        <a className="button" href="tel:132500">
          📞 VICSES 132 500
        </a>
        <SosControl sos={sos} shared={`your location${depth}`} undoSeconds={options.sos_undo_seconds} onSos={onSos} />
      </div>
      <p className="small muted">000 if anyone's life is in danger; VICSES for flood help, such as being trapped or water coming in.</p>
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
                    <span>{gradientSummary(o.route!)}</span>
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
        {accessNote(routes) && ` ${accessNote(routes)}`}
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
