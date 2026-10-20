import { useEffect, useState } from "react";
import { api, errorText } from "../api";
import { cm } from "../format";
import { LanguageSwitcher, useDocumentTitle, useI18n } from "../i18n/I18n";
import type { Options, ScenarioSummary } from "../types";
import {
  AID_CAP_NOTE,
  AID_LEVEL_BASIS,
  BODY_PART_BASIS,
  type Basised,
  DATASETS,
  FLOOD_DOCUMENTS,
  HARD_LIMIT_NOTE,
  LIMITS,
  MOBILITY_DOCUMENTS,
  PEOPLE_DOCUMENTS,
  type Work,
} from "./content";

const REPOSITORY = "https://github.com/TN019/flood-risk-aware-pedestrian-routing-system";

type Live = { options: Options; scenarios: ScenarioSummary[] } | { error: string } | null;

/** Where the data comes from and what each limit rests on. Reached only by its address, /reference. */
export function ReferencePage() {
  const { lang, t, rich } = useI18n();
  useDocumentTitle("ref.pageTitle");
  const [live, setLive] = useState<Live>(null);

  useEffect(() => {
    Promise.all([api.options(lang), api.scenarios(lang)])
      .then(([options, scenarios]) => setLive({ options, scenarios }))
      .catch((err: Error) => setLive({ error: errorText(err, t, err.message) }));
  }, [lang, t]);

  const values = live && "options" in live ? live : null;

  return (
    <main className="doc-page">
      <header>
        <div className="doc-top">
          <a className="back" href="/">
            {t("doc.back")}
          </a>
          <LanguageSwitcher />
        </div>
        <h1>{t("ref.title")}</h1>
        <p>{t("ref.intro")}</p>
        <nav aria-label={t("doc.sections")}>
          <a href="#data">{t("ref.nav.data")}</a>
          <a href="#scenarios">{t("ref.nav.scenarios")}</a>
          <a href="#limits">{t("ref.nav.limits")}</a>
          <a href="#documents">{t("ref.nav.documents")}</a>
          <a href="#licences">{t("ref.nav.licences")}</a>
          <a href="#not-covered">{t("ref.nav.notCovered")}</a>
        </nav>
      </header>

      <section id="data">
        <h2>{t("ref.data.title")}</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("ref.data.data")}</th>
                <th>{t("ref.data.use")}</th>
                <th>{t("ref.data.licence")}</th>
              </tr>
            </thead>
            <tbody>
              {DATASETS.map((d) => {
                const name = d.nameKey ? t(d.nameKey) : <span lang="en">{d.name}</span>;
                return (
                  <tr key={d.name}>
                    <td>
                      <strong>{d.url ? <a href={d.url}>{name}</a> : name}</strong>
                      <span className="muted" lang="en">
                        {d.publisher}
                      </span>
                    </td>
                    <td>{t(d.use)}</td>
                    <td lang="en">{d.licenceUrl ? <a href={d.licenceUrl}>{d.licence}</a> : d.licence}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section id="scenarios">
        <h2>{t("ref.scenarios.title")}</h2>
        <p>{t("ref.scenarios.intro")}</p>
        <LiveState live={live} />
        {values?.scenarios.map((s) => (
          <article key={s.id} className="scenario">
            <h3>
              {s.title}
              {s.typical_depth_m !== null && (
                <span className="muted"> · {t("ref.scenarios.typical", { depth: cm(s.typical_depth_m) })}</span>
              )}
            </h3>
            <p>{s.description}</p>
            {s.sources.length > 0 && (
              <ul>
                {s.sources.map((source) => (
                  <li key={source}>{source}</li>
                ))}
              </ul>
            )}
          </article>
        ))}
      </section>

      <section id="limits">
        <h2>{t("ref.limits.title")}</h2>
        <p>
          <BasisTag basis="Cited" /> {t("ref.limits.cited")} <BasisTag basis="Derived" /> {t("ref.limits.derived")}{" "}
          <BasisTag basis="Chosen" /> {t("ref.limits.chosen")}
        </p>
        <LiveState live={live} />
        {values && <Limits options={values.options} />}
      </section>

      <section id="documents">
        <h2>{t("ref.documents.title")}</h2>
        {lang !== "en" && <p className="muted small">{t("ref.documents.note")}</p>}
        <h3>{t("ref.documents.flooding")}</h3>
        <Works works={FLOOD_DOCUMENTS} />
        <h3>{t("ref.documents.people")}</h3>
        <Works works={PEOPLE_DOCUMENTS} />
        <h3>{t("ref.documents.mobility")}</h3>
        <Works works={MOBILITY_DOCUMENTS} />
      </section>

      <section id="licences">
        <h2>{t("ref.licences.title")}</h2>
        <ul>
          <li>
            {rich("ref.licences.software", {
              licence: (
                <a key="licence" href="https://www.apache.org/licenses/LICENSE-2.0">
                  Apache License 2.0
                </a>
              ),
            })}
          </li>
          <li>
            {rich("ref.licences.osm", {
              licence: (
                <a key="licence" href="https://opendatacommons.org/licenses/odbl/1-0/">
                  ODbL 1.0
                </a>
              ),
            })}
          </li>
          <li>{t("ref.licences.others")}</li>
        </ul>
      </section>

      <section id="not-covered">
        <h2>{t("ref.notCovered.title")}</h2>
        <p className="notice">{t("ref.notCovered.notice")}</p>
        <ul>
          {LIMITS.map((limit) => (
            <li key={limit}>{t(limit)}</li>
          ))}
        </ul>
      </section>

      <footer className="muted">
        {rich("ref.footer", {
          parameters: (
            <a key="parameters" href={`${REPOSITORY}/blob/main/docs/parameters.md`}>
              docs/parameters.md
            </a>
          ),
          architecture: (
            <a key="architecture" href={`${REPOSITORY}/blob/main/docs/architecture.md`}>
              docs/architecture.md
            </a>
          ),
        })}
      </footer>
    </main>
  );
}

function LiveState({ live }: { live: Live }) {
  const { t } = useI18n();
  if (live === null) return <p className="muted">{t("ref.loading")}</p>;
  if ("error" in live) return <p className="notice">{t("ref.loadError", { error: live.error })}</p>;
  return null;
}

function Limits({ options }: { options: Options }) {
  const { t } = useI18n();
  const h = options.reference_height_m;
  const height = Math.round(h * 100);
  const depthOf = (fraction: number | null) => (fraction === null ? options.dry_depth_m : Math.min(fraction * h, options.hard_limit_m));
  return (
    <>
      <h3>{t("ref.walking")}</h3>
      <p>{t("ref.walkingIntro", { height })}</p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{t("ref.choice")}</th>
              <th>{t("ref.depth")}</th>
              <th>{t("ref.basis")}</th>
            </tr>
          </thead>
          <tbody>
            {options.body_parts.map((p) => (
              <tr key={p.key}>
                <td>{p.label.charAt(0).toUpperCase() + p.label.slice(1)}</td>
                <td className="num">
                  {cm(depthOf(p.fraction))}
                  {p.fraction !== null && <span className="muted"> {t("ref.fraction", { fraction: p.fraction })}</span>}
                </td>
                <BasisCell basis={BODY_PART_BASIS[p.key]} />
              </tr>
            ))}
            <tr>
              <td>{t("ref.upperLimit")}</td>
              <td className="num">{t("ref.atMost", { depth: cm(options.hard_limit_m) })}</td>
              <BasisCell basis={{ basis: "Cited", note: HARD_LIMIT_NOTE }} />
            </tr>
          </tbody>
        </table>
      </div>

      <h3>{t("ref.aids")}</h3>
      <p>
        {t("ref.aidsIntro")} {t(AID_CAP_NOTE)}
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{t("ref.deviceLevel")}</th>
              <th>{t("ref.depth")}</th>
              <th>{t("ref.basis")}</th>
            </tr>
          </thead>
          <tbody>
            {options.mobility_aids.flatMap((aid) =>
              aid.levels.map((level, i) => (
                <tr key={`${aid.key}/${level.key}`} className={i === 0 ? "group-start" : undefined}>
                  <td>
                    {i === 0 && <strong>{aid.label.charAt(0).toUpperCase() + aid.label.slice(1)}: </strong>}
                    {level.label}
                    {i === aid.levels.length - 1 && <span className="muted"> {t("ref.cap")}</span>}
                  </td>
                  <td className="num">{cm(level.depth_m)}</td>
                  <BasisCell basis={AID_LEVEL_BASIS[`${aid.key}/${level.key}`]} />
                </tr>
              )),
            )}
          </tbody>
        </table>
      </div>

      <h3>{t("ref.levels")}</h3>
      <p>{t("ref.levelsIntro", { height })}</p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{t("ref.level")}</th>
              <th>{t("ref.typicalWater")}</th>
              <th>{t("ref.depth")}</th>
            </tr>
          </thead>
          <tbody>
            {options.flood_levels.map((level) => (
              <tr key={level.key}>
                <td>{level.label}</td>
                <td>{level.body_range}</td>
                <td className="num">
                  {level.upper_m === null ? t("ref.over", { depth: cm(level.lower_m) }) : `${cm(level.lower_m)}–${cm(level.upper_m)}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

const BASIS_KEY = { Cited: "basis.cited", Derived: "basis.derived", Chosen: "basis.chosen" } as const;

function BasisTag({ basis }: { basis: Basised["basis"] }) {
  const { t } = useI18n();
  return (
    <span className={`basis basis-${basis.toLowerCase()}`} title={basis === "Chosen" ? t("basis.chosenTitle") : undefined}>
      {t(BASIS_KEY[basis])}
    </span>
  );
}

function BasisCell({ basis }: { basis: Basised | undefined }) {
  const { t } = useI18n();
  if (!basis) return <td className="muted">{t("ref.seeParameters")}</td>;
  return (
    <td>
      <BasisTag basis={basis.basis} /> {t(basis.note)}
    </td>
  );
}

function Works({ works }: { works: Work[] }) {
  const { t } = useI18n();
  return (
    <ul className="works">
      {works.map((w) => (
        <li key={w.citation}>
          <cite lang="en">{w.url ? <a href={w.url}>{w.citation}</a> : w.citation}</cite>
          <span className="muted">{t(w.use)}</span>
        </li>
      ))}
    </ul>
  );
}
