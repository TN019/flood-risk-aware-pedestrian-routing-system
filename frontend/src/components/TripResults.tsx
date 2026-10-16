import { useEffect, useState } from "react";
import { cm, depthSummary, distance, minutes } from "../format";
import type { Options, RouteOption, TripPlan } from "../types";
import { COLOURS } from "./MapView";

interface Props {
  trip: TripPlan;
  options: Options;
  sosSentAt: number | null;
  onSos: (sentAt: number | null) => void;
  onUseLimit: (bodyPart: string) => void;
}

const SWATCH: Record<RouteOption["kind"], { colour: string; dash: string }> = {
  shortest: { colour: COLOURS.shortest, dash: "6 4" },
  safe_shortest: { colour: COLOURS.safe_shortest, dash: "1 5" },
  recommended: { colour: COLOURS.recommended, dash: "" },
};

function Swatch({ colour, dash, width = 5 }: { colour: string; dash: string; width?: number }) {
  return (
    <svg className="swatch" viewBox="0 0 28 10" aria-hidden="true">
      <line x1="2" y1="5" x2="26" y2="5" stroke={colour} strokeWidth={width} strokeDasharray={dash} strokeLinecap="round" />
    </svg>
  );
}

function OriginAlert({ trip }: { trip: TripPlan }) {
  const o = trip.origin;
  const depth = o.depth_m === null ? "water of unknown depth" : `${cm(o.depth_m)} of water`;
  const here = o.depth_m === null ? "unknown" : cm(o.depth_m);
  if (o.sheltered && !trip.has_safe_route) {
    return (
      <div className="alert alert-info" role="status">
        You are starting inside {trip.start.label}. No route keeps you within your limit, so the safest choice is to
        stay inside until the water goes down.
      </div>
    );
  }
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

function Emergency({ trip, options, sosSentAt, onSos }: Omit<Props, "onUseLimit">) {
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
      {only && <p>No shelter can be reached from here. Stay on the highest ground you can reach.</p>}
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

function Alternatives({ trip, options, onUseLimit }: Pick<Props, "trip" | "options" | "onUseLimit">) {
  const d = trip.downgrade;
  const r = trip.refuge;
  const refugeText = r && (
    <>
      <p>
        <strong>Shelter nearby: {r.name}</strong> ({r.entrance_label}), {distance(r.route.metrics.length_m)}, deepest water{" "}
        {depthSummary(r.route.metrics.max_depth_m, r.route.metrics.max_depth_label, options.dry_depth_m)}. Green on the map. Wait
        there until the water goes down; this is based on current conditions only.
      </p>
      {!r.within_limit && <p className="warn-text">⚠️ The way there crosses water deeper than your limit; it is the shallowest way out.</p>}
    </>
  );
  return (
    <>
      {d && (
        <section className="card option-card">
          <p>
            <strong>
              Accept water up to the {d.body_part_label} ({cm(d.depth_limit_m)})?
            </strong>{" "}
            Then you can get there: {distance(d.route.metrics.length_m)}, deepest{" "}
            {depthSummary(d.route.metrics.max_depth_m, d.route.metrics.max_depth_label, options.dry_depth_m)}.
          </p>
          <p className="legend-line">
            <Swatch colour={COLOURS.downgrade} dash="6 4" /> Dashed light purple on the map.
          </p>
          <button type="button" className="button" onClick={() => onUseLimit(d.body_part)}>
            Use the {d.body_part_label} limit
          </button>
        </section>
      )}
      {r &&
        (trip.origin.level === "critical" ? (
          <details className="card option-card">
            <summary>If you cannot wait for help: route to shelter</summary>
            {refugeText}
          </details>
        ) : (
          <section className="card option-card refuge">{refugeText}</section>
        ))}
    </>
  );
}

function Comparison({ trip, options }: Pick<Props, "trip" | "options">) {
  const routes = trip.routes!;
  return (
    <section className="card" aria-labelledby="compare-title">
      <h2 id="compare-title">Compare routes</h2>
      <ul className="compare">
        {routes.options.map((o) => {
          const m = o.route?.metrics;
          return (
            <li key={o.kind} className={o.kind === "recommended" ? "compare-main" : ""}>
              <div className="compare-name">
                <Swatch colour={SWATCH[o.kind].colour} dash={SWATCH[o.kind].dash} />
                <span>{o.name}</span>
              </div>
              {m ? (
                <div className="compare-values">
                  <span>
                    {distance(m.length_m)} · {minutes(m.travel_time_s)}
                    {m.detour_ratio && m.detour_ratio > 0.005 ? ` (+${Math.round(m.detour_ratio * 100)}%)` : ""}
                  </span>
                  <span>
                    Deepest {depthSummary(m.max_depth_m, m.max_depth_label, options.dry_depth_m)} · {distance(m.wading_length_m)} in water
                  </span>
                  {m.segments_over_limit > 0 && <span className="warn-text">{m.segments_over_limit} section(s) over your limit</span>}
                </div>
              ) : (
                <div className="compare-values warn-text">{o.error}</div>
              )}
            </li>
          );
        })}
      </ul>
      <p className="muted small">{routes.blocked_edges} network sections are over your limit in this scenario.</p>
    </section>
  );
}

export function TripResults(props: Props) {
  const { trip, options } = props;
  const recommended = trip.routes?.options.find((o) => o.kind === "recommended") ?? null;
  const m = recommended?.route?.metrics;
  const place = (p: TripPlan["start"], label: string | null | undefined) =>
    p.method === "point" ? "the selected point" : `${p.label}${label ? ` (${label})` : ""}`;

  return (
    <div className="results">
      <OriginAlert trip={trip} />
      <Emergency {...props} />
      {!trip.has_safe_route && <Alternatives {...props} />}
      {!trip.routes && <div className="alert alert-red">No route connects these points.</div>}
      {recommended && m && (
        <section className="card summary" aria-label="Recommended route">
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
              <span className="metric-value">{m.max_depth_m && m.max_depth_m > options.dry_depth_m ? cm(m.max_depth_m) : "Dry"}</span>
              <span className="metric-label">{m.max_depth_m && m.max_depth_m > options.dry_depth_m ? m.max_depth_label : "deepest water"}</span>
            </div>
            <div>
              <span className="metric-value">{distance(m.wading_length_m)}</span>
              <span className="metric-label">in water</span>
            </div>
          </div>
          <p className="muted small">
            From {place(trip.start, recommended.route?.from.label)} to {place(trip.destination, recommended.route?.to.label)}.
          </p>
        </section>
      )}
      {recommended && !recommended.found && <div className="alert alert-warn">{recommended.error}</div>}
      {trip.routes && <Comparison trip={trip} options={options} />}
    </div>
  );
}
