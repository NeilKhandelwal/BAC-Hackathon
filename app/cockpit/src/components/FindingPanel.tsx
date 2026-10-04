import { useState } from "react";
import type { CockpitData, MetricDef } from "../data/types";
import type { RunResult } from "../engine/run";
import { topReasons } from "../engine/run";
import type { Stability } from "../engine/rank";
import { fmtInt, fmtPct, fmtScore, fmtThreshold, fmtValue, ordinal } from "../lib/format";
import { Barcode } from "./Shortlist";

interface Props {
  data: CockpitData;
  result: RunResult;
  stability: Stability | null;
  /** true while rank stability still reflects the previous conditions */
  stabilityStale: boolean;
  idx: number | null;
  compare: number | null;
  onCompare: (i: number | null) => void;
  onClose: () => void;
  drawer: boolean;
  open: boolean;
  onToggle: () => void;
}

const LOUDOUN = "51107";

export function FindingPanel({ data, result, stability, stabilityStale, idx, compare, onCompare, onClose, drawer, open, onToggle }: Props) {
  if (idx === null) {
    return (
      <section className={`finding is-empty${drawer ? " is-drawer" : ""}`} aria-label="County finding">
        <p className="finding-hint">Select a county on the map or in the top 10 to see why it ranks where it does.</p>
      </section>
    );
  }
  const name = `${data.counties.name[idx]}, ${data.counties.state[idx]}`;
  const passed = !!result.gates.passed[idx];
  const rank = result.rankOf[idx]!;
  const loudoun = data.counties.fips.indexOf(LOUDOUN);
  const cmp = compare !== null && compare !== idx ? compare : null;

  return (
    <section className={`finding${drawer ? " is-drawer" : ""}${drawer && !open ? " is-collapsed" : ""}`} aria-label={`Finding for ${name}`}>
      <header className="finding-head">
        <div className="finding-title">
          <h2>{name}</h2>
          <p className="finding-rank">
            {passed ? (
              <>
                Rank <strong>{fmtInt(rank)}</strong> of {fmtInt(result.passedCount)}
                <span className="sep">·</span>
                Score <strong>{fmtScore(result.comp[idx]!)}</strong>
                {!result.floor[idx] && <span className="flag-fail">Below a pillar floor</span>}
              </>
            ) : (
              <span className="flag-fail">Excluded by {result.gates.failed[idx]!.length === 1 ? "a gate" : `${result.gates.failed[idx]!.length} gates`}</span>
            )}
          </p>
        </div>
        <div className="finding-actions">
          {cmp === null && loudoun >= 0 && loudoun !== idx && (
            <button className="btn btn-quiet" onClick={() => onCompare(loudoun)}>
              Compare with Loudoun, VA
            </button>
          )}
          {cmp !== null && (
            <button className="btn btn-quiet" onClick={() => onCompare(null)}>
              Stop comparing
            </button>
          )}
          {drawer && (
            <button className="btn btn-quiet" aria-expanded={open} onClick={onToggle}>
              {open ? "Collapse" : "Expand"}
            </button>
          )}
          <button className="btn btn-quiet" onClick={onClose} aria-label="Close finding">
            Close
          </button>
        </div>
      </header>

      {(!drawer || open) && (
        <div className="finding-body">
          <div className="fcol">
            <StabilityBlock data={data} result={result} stability={stability} stale={stabilityStale} idx={idx} />
            <GateBlock data={data} result={result} idx={idx} />
            <CoverageBlock data={data} result={result} idx={idx} />
          </div>
          <div className="fcol">
            <Contributions data={data} result={result} idx={idx} cmp={cmp} />
          </div>
          <div className="fcol">
            <Evidence data={data} result={result} idx={idx} />
            <Horizon data={data} result={result} idx={idx} />
          </div>
        </div>
      )}
    </section>
  );
}

function StabilityBlock({
  data,
  result,
  stability,
  stale,
  idx,
}: {
  data: CockpitData;
  result: RunResult;
  stability: Stability | null;
  stale: boolean;
  idx: number;
}) {
  // Check the current result first: a share from the previous conditions must
  // not outlive the county's exclusion or floor failure.
  const eligible = !!result.gates.passed[idx] && !!result.floor[idx];
  const share = stability?.share[idx];
  const tiers = stability?.tiers.get(idx);
  const has = eligible && share !== undefined && !Number.isNaN(share);
  return (
    <div className={`block stab-block${stale && has ? " is-stale" : ""}`} aria-busy={stale}>
      <h3>
        Rank stability
        {stale && has && <span className="h-note">Updating</span>}
      </h3>
      {has ? (
        <>
          <p className="stab-big">
            Top {result.topN} in <strong>{fmtPct(share!)}</strong> of {fmtInt(stability!.samples)} sampled weight scenarios
          </p>
          {tiers && <Barcode tiers={tiers} tall />}
          <p className="fine">
            {share! >= 0.9
              ? "Robust: the rank holds across most shifts in priorities."
              : share! >= 0.5
                ? "Moderately sensitive to how the pillars are weighted."
                : share! > 0
                  ? "Sensitive: a different weighting often moves it out of the top 10."
                  : "Never reaches the top 10 in the sampled scenarios."}
          </p>
        </>
      ) : (
        <p className="fine">
          {!result.gates.passed[idx]
            ? "Not computed: the county is excluded by a gate."
            : !result.floor[idx]
              ? "Not computed for counties below a pillar floor."
              : (stability?.warning ?? "Updating for the current conditions.")}
        </p>
      )}
      {data.meta.synthetic && <p className="fine">Computed on synthetic values.</p>}
    </div>
  );
}

function GateBlock({ data, result, idx }: { data: CockpitData; result: RunResult; idx: number }) {
  const c = result.conditions;
  const failed = new Set(result.gates.failed[idx]);
  const unknown = new Set(result.gates.unknown[idx]);
  const n = data.counties.fips.length;
  return (
    <div className="block">
      <h3>Hard gates</h3>
      <ul className="gate-status">
        {result.gates.active.map((g) => {
          const state = failed.has(g.key) ? "fail" : unknown.has(g.key) ? "unknown" : "pass";
          const v = data.values[g.column]?.[idx] ?? null;
          const m = data.metrics.find((x) => x.id === g.column);
          const t = c.gates[g.key];
          const thr = typeof t === "number" ? (g.kind === "capacity_multiple" ? `${fmtInt(t * c.facility.mw)} MW` : fmtThreshold(t, g.unit)) : "";
          return (
            <li key={g.key} className={`gs gs-${state}`}>
              <StatusIcon state={state} />
              <span className="gs-label">{g.label}</span>
              <span className="gs-detail">
                {state === "unknown"
                  ? "No data"
                  : g.kind === "flag"
                    ? v && v > 0
                      ? "Yes"
                      : "No"
                    : g.kind === "hazard_pct"
                      ? `${ordinal(result.hazardPct(g.column)[idx]!)} pct, max ${thr}`
                      : `${m ? fmtValue(v, m) : v}, limit ${thr}`}
              </span>
            </li>
          );
        })}
        {result.gates.active.length === 0 && <li className="fine">No gates are on.</li>}
      </ul>
      {n > 0 && unknown.size > 0 && <p className="fine">{data.meta.nullPolicy.description.gate}</p>}
    </div>
  );
}

function StatusIcon({ state }: { state: "pass" | "fail" | "unknown" }) {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden className="gs-icon">
      {state === "pass" && <path d="M2.5 7.5 L5.5 10.5 L11.5 3.5" fill="none" stroke="currentColor" strokeWidth="2" />}
      {state === "fail" && <path d="M3 3 L11 11 M11 3 L3 11" fill="none" stroke="currentColor" strokeWidth="2" />}
      {state === "unknown" && <circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeDasharray="2 2" />}
      <title>{state === "pass" ? "Passes" : state === "fail" ? "Fails" : "Unknown, no data"}</title>
    </svg>
  );
}

function CoverageBlock({ data, result, idx }: { data: CockpitData; result: RunResult; idx: number }) {
  const cov = result.hs.coverage[idx]!;
  const have = Math.round(cov * data.meta.coverageDenominator);
  return (
    <div className="block">
      <h3>Coverage</h3>
      <p>
        <strong>{fmtPct(cov)}</strong> of {data.meta.coverageDenominator} scored metrics have data ({have})
      </p>
      <div className="meter" aria-hidden>
        <span style={{ width: `${cov * 100}%` }} />
      </div>
      <p className="fine">
        {data.meta.missingColumns.length} metrics are not in the table yet. {data.meta.nullPolicy.description.pillar}
      </p>
    </div>
  );
}

function Contributions({ data, result, idx, cmp }: { data: CockpitData; result: RunResult; idx: number; cmp: number | null }) {
  const c = result.conditions;
  const exempt = new Set(c.floorExempt);
  const den = (i: number) => result.hs.pillars.reduce((a, p) => a + (Number.isNaN(result.hs.pillarScore[p]![i]!) ? 0 : result.weights[p]!), 0);
  const dA = den(idx);
  const dB = cmp !== null ? den(cmp) : 0;
  return (
    <div className="block">
      <h3>
        Pillar contributions
        <span className="h-note">score = sum of weighted pillar scores</span>
      </h3>
      {cmp !== null && (
        <p className="cmp-legend">
          <span className="cmp-a">{data.counties.name[idx]}</span> vs{" "}
          <span className="cmp-b">
            {data.counties.name[cmp]}, {data.counties.state[cmp]}
          </span>
          {!result.gates.passed[cmp] && <span className="flag-fail"> excluded by a gate</span>}
        </p>
      )}
      <table className="contrib">
        <colgroup>
          <col className="c-pillar" />
          <col className="c-weight" />
          <col className="c-bar" />
          <col className="c-adds" />
        </colgroup>
        <thead>
          <tr>
            <th scope="col">Pillar</th>
            <th scope="col" className="num">Weight</th>
            <th scope="col">Score, 0 to 100</th>
            <th scope="col" className="num">Adds</th>
          </tr>
        </thead>
        <tbody>
          {data.pillars.map((p) => {
            const s = result.hs.pillarScore[p.id]?.[idx] ?? NaN;
            const pct = result.hs.pillarPct[p.id]?.[idx] ?? NaN;
            const w = result.weights[p.id] ?? 0;
            const add = Number.isNaN(s) || dA === 0 ? NaN : (w * s) / dA;
            const below = w > 0 && !exempt.has(p.id) && !Number.isNaN(pct) && pct < c.floorPercentile;
            const sB = cmp !== null ? (result.hs.pillarScore[p.id]?.[cmp] ?? NaN) : NaN;
            return (
              <tr key={p.id} style={{ "--hue": `var(--p-${p.id}, var(--ink-2))` } as React.CSSProperties}>
                <th scope="row">
                  <span className="swatch" aria-hidden />
                  {p.label}
                  {below && <span className="flag-fail small"> below floor</span>}
                </th>
                <td className="num">{fmtPct(w)}</td>
                <td>
                  <span className="pbar-wrap">
                    <span className="pbar">
                      <span className="pbar-a" style={{ "--s": Number.isNaN(s) ? 0 : s / 100 } as React.CSSProperties} />
                      {cmp !== null && !Number.isNaN(sB) && <span className="pbar-b" style={{ left: `${sB}%` }} />}
                    </span>
                    <span className="pbar-v">{Number.isNaN(s) ? "No data" : fmtScore(s)}</span>
                  </span>
                </td>
                <td className="num">{Number.isNaN(add) ? "—" : `+${fmtScore(add)}`}</td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr>
            <th scope="row">Composite</th>
            <td />
            <td>{cmp !== null && <span className="fine">Tick marks show the comparison county.</span>}</td>
            <td className="num">
              <strong>{fmtScore(result.comp[idx]!)}</strong>
            </td>
          </tr>
        </tfoot>
      </table>
      {dB === 0 && cmp !== null && <p className="fine">The comparison county has no pillar data.</p>}
      <p className="fine">
        Pillar scores are national percentiles of the county's metrics. Floor: {c.floorPercentile}th percentile
        {c.floorExempt.length ? `, ${c.floorExempt.join(", ")} exempt` : ""}.
      </p>
    </div>
  );
}

function Evidence({ data, result, idx }: { data: CockpitData; result: RunResult; idx: number }) {
  const [all, setAll] = useState(false);
  const metricById = new Map(data.metrics.map((m) => [m.id, m]));
  const reasons = topReasons(result.hs, result.weights, idx, 3);
  const scored: { col: string; m: MetricDef; pct: number }[] = [];
  for (const p of result.hs.pillars) {
    for (const col of result.hs.columns[p]!) {
      const m = metricById.get(col);
      if (m) scored.push({ col, m: { ...m, pillar: p }, pct: result.hs.colPct[col]![idx]! });
    }
  }
  const weakest = scored
    .filter((x) => !Number.isNaN(x.pct) && (result.weights[x.m.pillar!] ?? 0) > 0)
    .sort((a, b) => a.pct - b.pct)
    .slice(0, 3);
  const rows = all ? scored : [...reasons.map((r) => scored.find((s) => s.col === r)!).filter(Boolean), ...weakest];
  return (
    <div className="block evidence">
      <h3>
        Evidence
        <button className="link" onClick={() => setAll((a) => !a)} aria-expanded={all}>
          {all ? "Show key rows" : `All ${scored.length} metrics`}
        </button>
      </h3>
      {!all && <p className="ev-group">Strongest, then weakest</p>}
      <table className="ev">
        <tbody>
          {rows.map(({ col, m, pct }, k) => (
            <tr key={`${col}-${k}`} style={{ "--hue": `var(--p-${m.pillar}, var(--ink-2))` } as React.CSSProperties}>
              <th scope="row">
                <span className="ev-label">
                  <span className="swatch" aria-hidden />
                  {m.label}
                </span>
                <span className="ev-s">{m.kind === "projected" ? <span className="proj-tag">Projected</span> : `Observed · ${m.source}`}</span>
              </th>
              <td className="num ev-v">{fmtValue(data.values[col]?.[idx], m)}</td>
              <td className="num ev-p">{Number.isNaN(pct) ? "" : `${ordinal(pct)} pct`}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="fine">Observed values with their source. Percentiles are national, 100 is best.</p>
    </div>
  );
}

const EMBER = ["var(--ember-1)", "var(--ember-2)", "var(--ember-3)", "var(--ember-4)", "var(--ember-5)"];

function Horizon({ data, result, idx }: { data: CockpitData; result: RunResult; idx: number }) {
  const scen = result.conditions.scenario;
  const pairs = data.metrics.filter((m) => m.horizon2050?.[scen]);
  const rankNow = result.conditions.horizon === 2026 ? result.rankOf[idx]! : result.rankOther[idx]!;
  const rank2050 = result.conditions.horizon === 2050 ? result.rankOf[idx]! : result.rankOther[idx]!;
  return (
    <div className="block horizon-block">
      <h3>
        Today and 2050
        <span className="proj-tag">Projected · {scen === "rcp85" ? "RCP8.5" : "RCP4.5"}</span>
      </h3>
      <table className="ember">
        <thead>
          <tr>
            <th />
            <th scope="col" className="num">
              Today
            </th>
            <th scope="col" className="num">
              2050
            </th>
          </tr>
        </thead>
        <tbody>
          {pairs.map((m) => {
            const fut = m.horizon2050![scen]!;
            const a = data.values[m.id]?.[idx] ?? null;
            const b = data.values[fut]?.[idx] ?? null;
            const all = [...(data.values[m.id] ?? []), ...(data.values[fut] ?? [])].filter((x): x is number => x !== null);
            const lo = Math.min(...all);
            const hi = Math.max(...all);
            const tone = (v: number | null) => (v === null ? "var(--ground)" : EMBER[Math.min(4, Math.floor(((v - lo) / (hi - lo || 1)) * 5))]);
            return (
              <tr key={m.id}>
                <th scope="row">{m.label}</th>
                <td className="num">
                  <span className="ember-chip" style={{ background: tone(a) }} />
                  {fmtValue(a, m)}
                </td>
                <td className="num">
                  <span className="ember-chip" style={{ background: tone(b) }} />
                  {fmtValue(b, m)}
                </td>
              </tr>
            );
          })}
          <tr className="ember-rank">
            <th scope="row">Rank</th>
            <td className="num">{rankNow ? fmtInt(rankNow) : "Excluded"}</td>
            <td className="num">{rank2050 ? fmtInt(rank2050) : "Excluded"}</td>
          </tr>
        </tbody>
      </table>
      <p className="fine">
        2050 replaces only the climate and water columns. Everything else is held at today's values. Ember color runs from the lowest to the
        highest value in either period.
      </p>
    </div>
  );
}
