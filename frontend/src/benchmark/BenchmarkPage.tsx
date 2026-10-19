import { type ReactNode, useEffect, useState } from "react";
import { api } from "../api";
import type { BenchmarkResults, Rate, Spread } from "./types";

const REPOSITORY = "https://github.com/TN019/flood-risk-aware-pedestrian-routing-system";

const pct = (x: number | null | undefined, digits = 0) => (x === null || x === undefined ? "—" : `${(x * 100).toFixed(digits)}%`);
const ms = (s: Spread) => (s.median === null ? "—" : `${s.median.toFixed(0)} ms (95th percentile ${s.p95?.toFixed(0)} ms)`);
const metres = (x: number | null) => (x === null ? "—" : `${Math.round(x)} m`);
const share = (n: number, of: number) => `${n} of ${of}`;
const rate = (r: Rate) => (r.of === 0 ? "—" : `${pct(r.rate, 1)} (${r.count} of ${r.of})`);

/** Whether a result came out as docs/benchmarks.md predicted, or is a measurement. */
function Verdict({ ok }: { ok?: boolean }) {
  if (ok === undefined) return <span className="verdict verdict-measured">Measured</span>;
  return <span className={`verdict ${ok ? "verdict-ok" : "verdict-bad"}`}>{ok ? "As predicted" : "Not as predicted"}</span>;
}

function Result({ title, ok, children }: { title: string; ok?: boolean; children: ReactNode }) {
  return (
    <article className="result">
      <h3>
        {title} <Verdict ok={ok} />
      </h3>
      {children}
    </article>
  );
}

/** What the routing engine shows about its correctness, safety and accessibility. Reached only by
 * its address, /benchmark. */
export function BenchmarkPage() {
  const [results, setResults] = useState<BenchmarkResults | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .benchmark()
      .then(setResults)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <main className="doc-page">
      <header>
        <a className="back" href="/">
          ← Southbank Flood Routes
        </a>
        <h1>Benchmarks</h1>
        <p>
          What the routing engine shows about its own correctness, the safety it gives and what that costs, and the accessibility of what it
          routes over. The predictions were written before the first run, in{" "}
          <a href={`${REPOSITORY}/blob/main/docs/benchmarks.md`}>docs/benchmarks.md</a>.
        </p>
        <p className="muted">
          The algorithms are tested on made-up data (a small test town) and on the real Southbank network. Whether the data matches the
          streets can only be checked on site: see Field inspection.
        </p>
        {results && (
          <p className="muted small">
            Run {new Date(results.generated_at).toLocaleString()} on commit {results.commit ?? "unknown"}; network of{" "}
            {results.network.nodes.toLocaleString()} junctions and {results.network.edges.toLocaleString()} sections.
          </p>
        )}
        <nav aria-label="Sections">
          <a href="#correctness">Correctness</a>
          <a href="#safety">Pedestrian safety</a>
          <a href="#access">Accessibility</a>
          <a href="#field">Field inspection</a>
          <a href="#performance">Performance</a>
        </nav>
      </header>

      {error && <p className="notice">The benchmark results could not be loaded: {error}</p>}
      {!results && !error && <p className="muted">Loading the results…</p>}
      {results && <Results r={results} />}

      <footer className="muted">
        Run them again with <code>uv run python scripts/benchmark.py</code> in <code>backend/</code>; the results are written to{" "}
        <code>docs/benchmark.json</code>.
      </footer>
    </main>
  );
}

function Results({ r }: { r: BenchmarkResults }) {
  const c = r.correctness;
  const np = c.dijkstra_node_pairs;
  const e2e = c.dijkstra_end_to_end;
  const mm = c.minimax_brute_force;
  const v = c.verification;
  const rising = r.safety.rising_flood;
  const sf = r.access.step_free_pairs;
  const levels = Object.entries(r.safety.cost.levels);
  const overLimit = levels.flatMap(([, l]) => Object.values(l.travellers)).reduce((n, t) => n + t.recommended_over_limit, 0);

  return (
    <>
      <section id="correctness">
        <h2>Correctness of the algorithms</h2>
        <Result title="Path finder against NetworkX" ok={np.cost_match === np.pairs && e2e.length_match === e2e.routes}>
          <p>
            Node to node: same cost for <strong>{share(np.cost_match, np.pairs)}</strong> random pairs ({np.same_path} with the identical
            path). Through the router, with snapping and access legs: same length for <strong>{share(e2e.length_match, e2e.routes)}</strong>{" "}
            random trips.
          </p>
        </Result>
        <Result title="Safest-path search against brute force" ok={mm.match === mm.pairs}>
          <p>
            The lowest possible deepest point, then the shortest path that deep, agreed with enumerating every path for{" "}
            <strong>{share(mm.match, mm.pairs)}</strong> node pairs on {mm.graphs} random graphs.
          </p>
        </Result>
        <Result title="Hand-derived predictions" ok={v.test_town.met === v.test_town.total && v.southbank.met === v.southbank.total}>
          <p>
            Test town cases A–I: <strong>{share(v.test_town.met, v.test_town.total)}</strong> met. Southbank properties R-A to R-H:{" "}
            <strong>{share(v.southbank.met, v.southbank.total)}</strong> met.
          </p>
          {[...v.test_town.not_met, ...v.southbank.not_met].length > 0 && (
            <ul>
              {[...v.test_town.not_met, ...v.southbank.not_met].map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          )}
        </Result>
        {c.faults && (
          <Result title="Fault injection" ok={c.faults.faults.every((f) => f.caught)}>
            <p>
              Each fault breaks one safety rule on purpose; the whole test suite then runs against the broken code. As written, the suite
              has {c.faults.baseline.failed} failures in {c.faults.baseline.passed + c.faults.baseline.failed} tests.
            </p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Fault</th>
                    <th>Tests failed</th>
                    <th>Test town cases failed</th>
                    <th>Caught</th>
                  </tr>
                </thead>
                <tbody>
                  {c.faults.faults.map((f) => (
                    <tr key={f.fault}>
                      <td>
                        <strong>{f.fault}</strong> {f.breaks}
                      </td>
                      <td className="num">{share(f.tests_failed, f.tests_run)}</td>
                      <td>{f.test_town_cases_failed.length ? f.test_town_cases_failed.join(", ") : <span className="muted">none</span>}</td>
                      <td>{f.caught ? "Yes" : <strong className="warn-text">No</strong>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Result>
        )}
      </section>

      <section id="safety">
        <h2>Pedestrian safety</h2>
        <Result title="Safety and what it costs" ok={overLimit === 0}>
          <p>
            {r.safety.cost.trips} random trips at each flood level. No recommended route crossed water over the traveller's limit in{" "}
            {levels.length * Object.keys(levels[0]?.[1].travellers ?? {}).length * r.safety.cost.trips} plans
            {overLimit > 0 && <strong className="warn-text"> ({overLimit} did)</strong>}. Where the plain shortest way crosses water over the
            limit, the recommended route is longer by the median shown and avoids the median length of water over the limit.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Level and traveller</th>
                  <th>Route within the limit</th>
                  <th>Shortest way unsafe</th>
                  <th>Longer by</th>
                  <th>Water over the limit avoided</th>
                  <th>Without a route, offered</th>
                </tr>
              </thead>
              <tbody>
                {levels.flatMap(([key, level]) =>
                  Object.entries(level.travellers).map(([name, t], i) => (
                    <tr key={`${key}/${name}`} className={i === 0 ? "group-start" : undefined}>
                      <td>
                        {i === 0 && <strong>{level.title}: </strong>}
                        {name}
                      </td>
                      <td className="num">{share(t.with_route, r.safety.cost.trips)}</td>
                      <td className="num">{t.shortest_unsafe}</td>
                      <td className="num">{t.shortest_unsafe ? pct(t.detour_median) : "—"}</td>
                      <td className="num">{t.shortest_unsafe ? metres(t.over_limit_avoided_m_median) : "—"}</td>
                      <td>
                        {Object.entries(t.without_route)
                          .map(([what, n]) => `${what} ${n}`)
                          .join(", ") || <span className="muted">—</span>}
                      </td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          </div>
        </Result>
        <Result title="Rising flood: rerouting on the way" ok={rising.violations_m === 0 && !rising.outcomes.nothing}>
          <p>
            {rising.trips} trips for an {rising.traveller} traveller walking while the flood rises:{" "}
            {rising.schedule.map((s) => `${s.level.toLowerCase()} from ${Math.round(s.from_s / 60)} min`).join(", ")}. At every rise the
            trip is planned again from where they are.
          </p>
          <ul>
            <li>
              Walked in water over the limit on a route given as within it: <strong>{metres(rising.violations_m)}</strong>.
            </li>
            <li>
              Rerouted {rising.reroutes} times, in {rising.trips_rerouted} trips; {rising.caught_by_rising_water} times the water had risen
              over the limit where they stood, and the safest way out crossed {metres(rising.escape_over_limit_m)} of it in all.
            </li>
            <li>
              Outcomes:{" "}
              {Object.entries(rising.outcomes)
                .map(([what, n]) => `${what} ${n}`)
                .join(", ")}
              .
            </li>
            <li>
              Arrivals walked {pct(rising.extra_walk_median, 1)} further than first planned (median; 90th percentile{" "}
              {pct(rising.extra_walk_p90, 1)}).
            </li>
          </ul>
          {rising.not_replanned_outside_area > 0 && (
            <p className="notice">
              <strong>Finding:</strong> {rising.not_replanned_outside_area} times the flood rose while the route ran through the network's
              margin outside Southbank, where no trip can be planned (a start must lie inside). The traveller kept to the route they had and
              walked {metres(rising.over_limit_outside_area_m)} over the limit there in all. Replanning should work from anywhere on the
              network a route can take.
            </p>
          )}
        </Result>
      </section>

      <section id="access">
        <h2>Public area accessibility</h2>
        <Result title="Step-free connectivity between buildings" ok={sf.step_free_using_steps === 0 && sf.step_free_cheaper === 0}>
          <p>
            {sf.pairs} random pairs of buildings connected on foot, normal conditions: a step-free route exists for{" "}
            <strong>{share(sf.step_free_route, sf.pairs)}</strong>, and for {sf.same_length} it is the walking route itself (no steps on
            the way). Over all pairs it is longer by {pct(sf.longer_median, 1)} at the median, {pct(sf.longer_p90, 1)} at the 90th
            percentile and {pct(sf.longer_max, 1)} at most. No
            step-free route uses steps ({sf.step_free_using_steps}) or costs less than the walking route ({sf.step_free_cheaper}).
            {sf.step_free_shorter > 0 &&
              ` ${sf.step_free_shorter} ${sf.step_free_shorter === 1 ? "is" : "are"} shorter in metres but cost more: routes minimise walking cost, with a carriageway counted three times its length.`}
          </p>
        </Result>
      </section>

      <section id="field">
        <h2>Field inspection</h2>
        {r.field ? (
          <Result title="Model against the inspection">
            <ul>
              <li>
                Paths inspected: {r.field.paths.inspected}. Treated as walkable but not passable on site:{" "}
                <strong>{rate(r.field.paths.false_accessible)}</strong>. Treated as step-free but not: <strong>{rate(r.field.paths.false_step_free)}</strong>.
              </li>
              <li>
                Steps: the model agrees for {rate(r.field.paths.steps_agree)}; it misses steps on {rate(r.field.paths.steps_missed)} of sections it
                shows without them.
              </li>
              <li>
                Entrances inspected: {r.field.entrances.inspected}. Not there or not open to the public: {rate(r.field.entrances.not_usable)}; not
                step-free: {rate(r.field.entrances.not_step_free)}.
              </li>
            </ul>
          </Result>
        ) : (
          <>
            <p>
              No inspection has been filed yet. The data comes from OpenStreetMap, which can miss steps, kerbs, barriers and closures, or mark
              an entrance that is not open to the public; only an inspection on site can tell.
            </p>
            <ol>
              <li>
                <code>uv run python scripts/ground_truth_sample.py</code> draws footpath sections of each kind and building entrances, and writes a
                checklist with what the model says about each.
              </li>
              <li>On site, fill in each item: passable, steps, kerb ramp, gradient, width, surface, barriers, entrance step-free and open.</li>
              <li>
                File it as <code>data/ground_truth/inspected.csv</code>; <code>scripts/ground_truth_compare.py</code> and the next benchmark run
                report the agreement, and above all the share the model treats as usable that is not.
              </li>
            </ol>
          </>
        )}
      </section>

      <section id="performance">
        <h2>Performance</h2>
        <Result title="Planning time">
          <ul>
            {Object.entries(r.performance.plan_ms).map(([key, s]) => (
              <li key={key}>
                {r.safety.cost.levels[key]?.title ?? key}: a whole trip plan takes {ms(s)}, over {s.plans} plans.
              </li>
            ))}
            <li>One shortest-path search on the network: {ms(np.ours_ms)}; a trip through the router: {ms(e2e.route_ms)}.</li>
          </ul>
          <p className="muted small">The whole run took {Math.round(Object.values(r.performance.seconds).reduce((a, b) => a + b, 0) / 60)} minutes.</p>
        </Result>
      </section>
    </>
  );
}

