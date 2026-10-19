import { useEffect, useState } from "react";
import { api } from "../api";
import { cm } from "../format";
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
  const [live, setLive] = useState<Live>(null);

  useEffect(() => {
    Promise.all([api.options(), api.scenarios()])
      .then(([options, scenarios]) => setLive({ options, scenarios }))
      .catch((err: Error) => setLive({ error: err.message }));
  }, []);

  const values = live && "options" in live ? live : null;

  return (
    <main className="doc-page">
      <header>
        <a className="back" href="/">
          ← Southbank Flood Routes
        </a>
        <h1>Sources and references</h1>
        <p>
          Where the map, the network and the flood scenarios come from, and what every depth limit rests on. The values in the tables are read
          from the running system, so they are the ones routes use.
        </p>
        <nav aria-label="Sections">
          <a href="#data">Data</a>
          <a href="#scenarios">Flood scenarios</a>
          <a href="#limits">Depth limits</a>
          <a href="#documents">Documents</a>
          <a href="#licences">Licences</a>
          <a href="#not-covered">Not covered</a>
        </nav>
      </header>

      <section id="data">
        <h2>Data</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Data</th>
                <th>Used for</th>
                <th>Licence</th>
              </tr>
            </thead>
            <tbody>
              {DATASETS.map((d) => (
                <tr key={d.name}>
                  <td>
                    <strong>{d.url ? <a href={d.url}>{d.name}</a> : d.name}</strong>
                    <span className="muted">{d.publisher}</span>
                  </td>
                  <td>{d.use}</td>
                  <td>{d.licenceUrl ? <a href={d.licenceUrl}>{d.licence}</a> : d.licence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section id="scenarios">
        <h2>Flood scenarios</h2>
        <p>
          Each scenario is a published water level applied to the ground model: river and storm tide, drains backing up at high tide, and
          rain ponding in low spots. Its flood level is set by the typical depth on flooded footpaths.
        </p>
        <LiveState live={live} />
        {values?.scenarios.map((s) => (
          <article key={s.id} className="scenario">
            <h3>
              {s.title}
              {s.typical_depth_m !== null && <span className="muted"> · typical depth {cm(s.typical_depth_m)}</span>}
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
        <h2>Depth limits</h2>
        <p>
          <BasisTag basis="Cited" /> taken from a named source. <BasisTag basis="Derived" /> worked out from cited values.{" "}
          <BasisTag basis="Chosen" /> no source sets the value, so it is chosen; these are the first to revisit when better evidence appears.
        </p>
        <LiveState live={live} />
        {values && <Limits options={values.options} />}
      </section>

      <section id="documents">
        <h2>Documents</h2>
        <h3>Flooding in Southbank</h3>
        <Works works={FLOOD_DOCUMENTS} />
        <h3>People in floodwater and access</h3>
        <Works works={PEOPLE_DOCUMENTS} />
        <h3>Wheelchairs and mobility scooters</h3>
        <Works works={MOBILITY_DOCUMENTS} />
      </section>

      <section id="licences">
        <h2>Licences</h2>
        <ul>
          <li>
            The software is licensed under the <a href="https://www.apache.org/licenses/LICENSE-2.0">Apache License 2.0</a>.
          </li>
          <li>
            Data derived from OpenStreetMap, such as the processed walking network, is available under the{" "}
            <a href="https://opendatacommons.org/licenses/odbl/1-0/">ODbL 1.0</a> and credits © OpenStreetMap contributors.
          </li>
          <li>The other datasets keep the licences listed above. The documents are cited, not redistributed.</li>
        </ul>
      </section>

      <section id="not-covered">
        <h2>Not covered</h2>
        <p className="notice">
          This is not an official flood warning service. Follow warnings from VICSES and the Bureau of Meteorology, call 000 in an
          emergency, and call VICSES on 132 500 for flood or storm help.
        </p>
        <ul>
          {LIMITS.map((limit) => (
            <li key={limit}>{limit}</li>
          ))}
        </ul>
      </section>

      <footer className="muted">
        Every parameter, where it is set and why: <a href={`${REPOSITORY}/blob/main/docs/parameters.md`}>docs/parameters.md</a>. How the
        system works: <a href={`${REPOSITORY}/blob/main/docs/architecture.md`}>docs/architecture.md</a>.
      </footer>
    </main>
  );
}

function LiveState({ live }: { live: Live }) {
  if (live === null) return <p className="muted">Loading the current values…</p>;
  if ("error" in live) return <p className="notice">The current values could not be loaded: {live.error}</p>;
  return null;
}

function Limits({ options }: { options: Options }) {
  const h = options.reference_height_m;
  const depthOf = (fraction: number | null) => (fraction === null ? options.dry_depth_m : Math.min(fraction * h, options.hard_limit_m));
  return (
    <>
      <h3>Walking</h3>
      <p>
        Travellers choose the deepest water they will walk through as a part of the body; it becomes a depth from their height. Depths below
        are for a {Math.round(h * 100)} cm adult.
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Choice</th>
              <th>Depth</th>
              <th>Basis</th>
            </tr>
          </thead>
          <tbody>
            {options.body_parts.map((p) => (
              <tr key={p.key}>
                <td>{p.label.charAt(0).toUpperCase() + p.label.slice(1)}</td>
                <td className="num">
                  {cm(depthOf(p.fraction))}
                  {p.fraction !== null && <span className="muted"> ({p.fraction} × height)</span>}
                </td>
                <BasisCell basis={BODY_PART_BASIS[p.key]} />
              </tr>
            ))}
            <tr>
              <td>Upper limit for everyone</td>
              <td className="num">at most {cm(options.hard_limit_m)}</td>
              <BasisCell basis={{ basis: "Cited", note: HARD_LIMIT_NOTE }} />
            </tr>
          </tbody>
        </table>
      </div>

      <h3>Wheelchairs and mobility scooters</h3>
      <p>
        Travellers with a wheeled mobility aid choose a level of their device instead, and are never routed over steps or paths steeper than
        1:14, the steepest ramp AS 1428.1 allows. Every route shows its steepest and gentlest measured gradient. {AID_CAP_NOTE}
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Device and level</th>
              <th>Depth</th>
              <th>Basis</th>
            </tr>
          </thead>
          <tbody>
            {options.mobility_aids.flatMap((aid) =>
              aid.levels.map((level, i) => (
                <tr key={`${aid.key}/${level.key}`} className={i === 0 ? "group-start" : undefined}>
                  <td>
                    {i === 0 && <strong>{aid.label.charAt(0).toUpperCase() + aid.label.slice(1)}: </strong>}
                    {level.label}
                    {i === aid.levels.length - 1 && <span className="muted"> (cap)</span>}
                  </td>
                  <td className="num">{cm(level.depth_m)}</td>
                  <BasisCell basis={AID_LEVEL_BASIS[`${aid.key}/${level.key}`]} />
                </tr>
              )),
            )}
          </tbody>
        </table>
      </div>

      <h3>Flood levels</h3>
      <p>
        The four levels are named by where the typical water reaches on a {Math.round(h * 100)} cm adult: the ankle, knee and hip waterlines
        used to grade flood severity (Feng, Brenner &amp; Sester, 2020), with body heights from Drillis &amp; Contini (1966).
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Level</th>
              <th>Typical water</th>
              <th>Depth</th>
            </tr>
          </thead>
          <tbody>
            {options.flood_levels.map((level) => (
              <tr key={level.key}>
                <td>{level.label}</td>
                <td>{level.body_range}</td>
                <td className="num">
                  {level.upper_m === null ? `over ${cm(level.lower_m)}` : `${cm(level.lower_m)}–${cm(level.upper_m)}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function BasisTag({ basis }: { basis: Basised["basis"] }) {
  return (
    <span className={`basis basis-${basis.toLowerCase()}`} title={basis === "Chosen" ? "A judgement" : undefined}>
      {basis === "Chosen" ? "Judgement" : basis}
    </span>
  );
}

function BasisCell({ basis }: { basis: Basised | undefined }) {
  if (!basis) return <td className="muted">See docs/parameters.md</td>;
  return (
    <td>
      <BasisTag basis={basis.basis} /> {basis.note}
    </td>
  );
}

function Works({ works }: { works: Work[] }) {
  return (
    <ul className="works">
      {works.map((w) => (
        <li key={w.citation}>
          <cite>{w.url ? <a href={w.url}>{w.citation}</a> : w.citation}</cite>
          <span className="muted">{w.use}</span>
        </li>
      ))}
    </ul>
  );
}
