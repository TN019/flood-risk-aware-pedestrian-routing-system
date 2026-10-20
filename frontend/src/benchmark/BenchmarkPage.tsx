import { type ReactNode, useEffect, useState } from "react";
import { api, errorText } from "../api";
import { LanguageSwitcher, useDocumentTitle, useI18n } from "../i18n/I18n";
import type { ScenarioSummary } from "../types";
import type { BenchmarkResults } from "./types";
import { faultText, OUTCOMES, TRAVELLERS, words } from "./vocabulary";

const REPOSITORY = "https://github.com/TN019/flood-risk-aware-pedestrian-routing-system";

const pct = (x: number | null | undefined, digits = 0) => (x === null || x === undefined ? "—" : `${(x * 100).toFixed(digits)}%`);
const metres = (x: number | null) => (x === null ? "—" : `${Math.round(x)} m`);

/** Whether a result came out as docs/benchmarks.md predicted, or is a measurement. */
function Verdict({ ok }: { ok?: boolean }) {
  const { t } = useI18n();
  if (ok === undefined) return <span className="verdict verdict-measured">{t("bench.measured")}</span>;
  return <span className={`verdict ${ok ? "verdict-ok" : "verdict-bad"}`}>{ok ? t("bench.asPredicted") : t("bench.notAsPredicted")}</span>;
}

function Result({ title, ok, children }: { title: string; ok?: boolean; children: ReactNode }) {
  return (
    <article className="result">
      <h4>
        {title} <Verdict ok={ok} />
      </h4>
      {children}
    </article>
  );
}

/** What the routing engine shows about its correctness, safety and accessibility. Reached only by
 * its address, /benchmark. */
export function BenchmarkPage() {
  const { lang, t, rich } = useI18n();
  useDocumentTitle("bench.pageTitle");
  const [results, setResults] = useState<BenchmarkResults | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .benchmark(lang)
      .then(setResults)
      .catch((err: Error) => setError(errorText(err, t, err.message)));
    // The flood levels' titles, in the language shown.
    api
      .scenarios(lang)
      .then(setScenarios)
      .catch(() => undefined);
  }, [lang, t]);

  return (
    <main className="doc-page">
      <header>
        <div className="doc-top">
          <a className="back" href="/">
            {t("doc.back")}
          </a>
          <LanguageSwitcher />
        </div>
        <h1>{t("bench.title")}</h1>
        <p>
          {rich("bench.intro", {
            benchmarks: (
              <a key="benchmarks" href={`${REPOSITORY}/blob/main/docs/benchmarks.md`}>
                docs/benchmarks.md
              </a>
            ),
          })}
        </p>
        {results && (
          <p className="muted small">
            {t("bench.run", {
              date: new Date(results.generated_at).toLocaleString(lang === "en" ? "en-AU" : lang),
              commit: results.commit ?? t("bench.unknownCommit"),
              nodes: results.network.nodes.toLocaleString("en-AU"),
              edges: results.network.edges.toLocaleString("en-AU"),
            })}
          </p>
        )}
      </header>

      {error && <p className="notice">{t("bench.loadError", { error })}</p>}
      {!results && !error && <p className="muted">{t("bench.loading")}</p>}
      {results && <Results r={results} scenarios={scenarios} />}

      <footer className="muted">
        {rich("bench.footer", {
          command: <code key="command">uv run python scripts/benchmark.py</code>,
          folder: <code key="folder">backend/</code>,
          file: <code key="file">docs/benchmark.json</code>,
        })}
      </footer>
    </main>
  );
}

function Results({ r, scenarios }: { r: BenchmarkResults; scenarios: ScenarioSummary[] }) {
  const { t, rich, plural } = useI18n();
  const c = r.correctness;
  const np = c.dijkstra_node_pairs;
  const e2e = c.dijkstra_end_to_end;
  const mm = c.minimax_brute_force;
  const v = c.verification;
  const rising = r.safety.rising_flood;
  const sf = r.access.step_free_pairs;
  const levels = Object.entries(r.safety.cost.levels);
  const overLimit = levels.flatMap(([, l]) => Object.values(l.travellers)).reduce((n, tr) => n + tr.recommended_over_limit, 0);
  const share = (count: number, total: number) => t("bench.share", { count, total });
  const strong = (key: string, text: string) => <strong key={key}>{text}</strong>;
  // A level's title in the language shown; the schedule names levels only by their English title.
  const levelTitle = (key: string, english: string) => scenarios.find((s) => s.id === key)?.title ?? english;
  const titleOf = (english: string) => {
    const key = levels.find(([, l]) => l.title === english)?.[0];
    return key ? levelTitle(key, english) : english;
  };
  const offered = (counts: Record<string, number>) =>
    Object.entries(counts)
      .map(([what, n]) => `${words(t, OUTCOMES, what)} ${n}`)
      .join(", ");

  return (
    <>
      <section id="algorithm">
        <h2>{t("bench.algorithm")}</h2>
        <h3 className="group">{t("bench.correctness")}</h3>
        <Result title={t("bench.pathFinder")} ok={np.cost_match === np.pairs && e2e.length_match === e2e.routes}>
          <p>
            {rich("bench.pathFinderText", {
              pairs: strong("pairs", share(np.cost_match, np.pairs)),
              same: np.same_path,
              routes: strong("routes", share(e2e.length_match, e2e.routes)),
            })}
          </p>
        </Result>
        <Result title={t("bench.minimax")} ok={mm.match === mm.pairs}>
          <p>{rich("bench.minimaxText", { pairs: strong("pairs", share(mm.match, mm.pairs)), graphs: mm.graphs })}</p>
        </Result>
        <Result title={t("bench.predictions")} ok={v.test_town.met === v.test_town.total && v.southbank.met === v.southbank.total}>
          <p>
            {rich("bench.predictionsText", {
              town: strong("town", share(v.test_town.met, v.test_town.total)),
              southbank: strong("southbank", share(v.southbank.met, v.southbank.total)),
            })}
          </p>
          {[...v.test_town.not_met, ...v.southbank.not_met].length > 0 && (
            <ul lang="en">
              {[...v.test_town.not_met, ...v.southbank.not_met].map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          )}
        </Result>
        {c.faults && (
          <Result title={t("bench.faults")} ok={c.faults.faults.every((f) => f.caught)}>
            <p>
              {t("bench.faultsText", {
                failed: c.faults.baseline.failed,
                tests: c.faults.baseline.passed + c.faults.baseline.failed,
              })}
            </p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("bench.fault")}</th>
                    <th>{t("bench.testsFailed")}</th>
                    <th>{t("bench.casesFailed")}</th>
                    <th>{t("bench.caught")}</th>
                  </tr>
                </thead>
                <tbody>
                  {c.faults.faults.map((f) => (
                    <tr key={f.fault}>
                      <td>
                        <strong>{f.fault}</strong> {faultText(t, f.fault, f.breaks)}
                      </td>
                      <td className="num">{share(f.tests_failed, f.tests_run)}</td>
                      <td>
                        {f.test_town_cases_failed.length ? f.test_town_cases_failed.join(", ") : <span className="muted">{t("bench.none")}</span>}
                      </td>
                      <td>{f.caught ? t("bench.yes") : <strong className="warn-text">{t("bench.no")}</strong>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Result>
        )}
        <h3 className="group">{t("bench.safety")}</h3>
        <Result title={t("bench.cost")} ok={overLimit === 0}>
          <p>
            {rich("bench.costText", {
              trips: r.safety.cost.trips,
              plans: levels.length * Object.keys(levels[0]?.[1].travellers ?? {}).length * r.safety.cost.trips,
              overLimit:
                overLimit > 0 ? (
                  <strong key="over" className="warn-text">
                    {t("bench.costOverLimit", { count: overLimit })}
                  </strong>
                ) : (
                  ""
                ),
            })}
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("bench.levelTraveller")}</th>
                  <th>{t("bench.withRoute")}</th>
                  <th>{t("bench.shortestUnsafe")}</th>
                  <th>{t("bench.longerBy")}</th>
                  <th>{t("bench.avoided")}</th>
                  <th>{t("bench.offered")}</th>
                </tr>
              </thead>
              <tbody>
                {levels.flatMap(([key, level]) =>
                  Object.entries(level.travellers).map(([name, tr], i) => (
                    <tr key={`${key}/${name}`} className={i === 0 ? "group-start" : undefined}>
                      <td>
                        {i === 0 && <strong>{levelTitle(key, level.title)}: </strong>}
                        {words(t, TRAVELLERS, name)}
                      </td>
                      <td className="num">{share(tr.with_route, r.safety.cost.trips)}</td>
                      <td className="num">{tr.shortest_unsafe}</td>
                      <td className="num">{tr.shortest_unsafe ? pct(tr.detour_median) : "—"}</td>
                      <td className="num">{tr.shortest_unsafe ? metres(tr.over_limit_avoided_m_median) : "—"}</td>
                      <td>{offered(tr.without_route) || <span className="muted">—</span>}</td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          </div>
        </Result>
        <Result title={t("bench.rising")} ok={rising.violations_m === 0 && !rising.outcomes.nothing}>
          <p>
            {t("bench.risingText", {
              trips: rising.trips,
              traveller: words(t, TRAVELLERS, rising.traveller),
              schedule: rising.schedule
                .map((s) => t("bench.risingFrom", { level: titleOf(s.level).toLowerCase(), minutes: Math.round(s.from_s / 60) }))
                .join(", "),
            })}
          </p>
          <ul>
            <li>{rich("bench.risingViolations", { metres: strong("metres", metres(rising.violations_m)) })}</li>
            <li>
              {t("bench.risingReroutes", {
                reroutes: rising.reroutes,
                trips: rising.trips_rerouted,
                caught: rising.caught_by_rising_water,
                metres: metres(rising.escape_over_limit_m),
              })}
            </li>
            <li>{t("bench.risingOutcomes", { outcomes: offered(rising.outcomes) })}</li>
            <li>{t("bench.risingExtra", { median: pct(rising.extra_walk_median, 1), p90: pct(rising.extra_walk_p90, 1) })}</li>
          </ul>
          {rising.not_replanned_outside_area > 0 && (
            <p className="notice">
              <strong>{t("bench.finding")}</strong>{" "}
              {t("bench.findingText", { count: rising.not_replanned_outside_area, metres: metres(rising.over_limit_outside_area_m) })}
            </p>
          )}
        </Result>
        <h3 className="group">{t("bench.access")}</h3>
        <Result
          title={t("bench.stepFree")}
          ok={sf.step_free_using_steps === 0 && sf.step_free_using_steep === 0 && sf.step_free_cheaper === 0}
        >
          <p>
            {rich("bench.stepFreeText", {
              pairs: sf.pairs,
              steep: sf.walking_using_steep,
              routes: strong("routes", share(sf.step_free_route, sf.pairs)),
              same: sf.same_length,
              median: pct(sf.longer_median, 1),
              p90: pct(sf.longer_p90, 1),
              max: pct(sf.longer_max, 1),
              steps: sf.step_free_using_steps,
              steepUsed: sf.step_free_using_steep,
              cheaper: sf.step_free_cheaper,
            })}
            {sf.step_free_shorter > 0 && ` ${plural("bench.stepFreeShorter", sf.step_free_shorter)}`}
          </p>
        </Result>
      </section>
    </>
  );
}
