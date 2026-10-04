import { useLayoutEffect, useRef } from "react";
import type { CockpitData } from "../data/types";
import type { RunResult } from "../engine/run";
import type { Stability } from "../engine/rank";
import type { RankChanges } from "../state/changes";
import { fmtInt, fmtPct, fmtScore } from "../lib/format";

interface Props {
  data: CockpitData;
  result: RunResult;
  stability: Stability | null;
  stabilityStale: boolean;
  changes: RankChanges;
  selected: number | null;
  compare: number | null;
  onSelect: (i: number) => void;
}

const reduced = () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function Shortlist({ data, result, stability, stabilityStale, changes, selected, compare, onSelect }: Props) {
  const top = result.ranked.slice(0, result.topN);
  const listRef = useRef<HTMLOListElement>(null);
  const prevTops = useRef(new Map<number, number>());

  // FLIP: rows travel from where they were to where they are.
  useLayoutEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const rows = Array.from(list.querySelectorAll<HTMLElement>("[data-idx]"));
    const next = new Map<number, number>();
    for (const el of rows) next.set(Number(el.dataset.idx), el.offsetTop);
    if (!reduced()) {
      for (const el of rows) {
        const i = Number(el.dataset.idx);
        const was = prevTops.current.get(i);
        const now = next.get(i)!;
        if (was === undefined) {
          if (prevTops.current.size > 0)
            el.animate([{ transform: "translateY(24px)", opacity: 0.2 }, { transform: "none", opacity: 1 }], {
              duration: 420,
              easing: "cubic-bezier(0.2, 0, 0, 1)",
            });
        } else if (was !== now) {
          el.animate([{ transform: `translateY(${was - now}px)` }, { transform: "none" }], {
            duration: 420,
            easing: "cubic-bezier(0.2, 0, 0, 1)",
          });
        }
      }
    }
    prevTops.current = next;
  }, [top.join(",")]);

  const samples = stability?.samples ?? 0;

  return (
    <section className="shortlist" aria-labelledby="shortlist-h">
      <div className="shortlist-head">
        <h2 id="shortlist-h">Top {result.topN}</h2>
        <span className="shortlist-meta">of {fmtInt(result.passedCount)} gate-passing counties</span>
      </div>
      <p className="change-line" aria-live="polite">
        {changes.cause ? (
          <>
            <span className="change-cause">{changes.cause}</span>
            <span className="change-summary">{changes.summary}</span>
          </>
        ) : (
          <span className="change-summary">Change a weight, gate, preset, or horizon to see ranks move.</span>
        )}
      </p>
      <div className="cols" aria-hidden>
        <span>Rank</span>
        <span>County</span>
        <span className="num">Score</span>
        <span>Rank stability</span>
      </div>
      {top.length === 0 ? (
        <EmptyShortlist data={data} result={result} />
      ) : (
        <ol className="rows" ref={listRef}>
          {top.map((i, r) => {
            const d = changes.delta.get(i);
            const isNew = changes.entered.has(i);
            const share = stability?.share[i];
            const tiers = stability?.tiers.get(i);
            return (
              <li key={i} data-idx={i} className={`row${selected === i ? " is-selected" : ""}${compare === i ? " is-compare" : ""}`}>
                <button className="row-btn" onClick={() => onSelect(i)} aria-pressed={selected === i}>
                  <span className="rank">{r + 1}</span>
                  <span className="move">
                    {isNew ? (
                      <span className="tag tag-new">New</span>
                    ) : d ? (
                      <span className={`tag ${d > 0 ? "tag-up" : "tag-down"}`}>
                        <Arrow up={d > 0} />
                        {Math.abs(d)}
                        <span className="visually-hidden">{d > 0 ? " up" : " down"}</span>
                      </span>
                    ) : null}
                  </span>
                  <span className="who">
                    <span className="who-name">{data.counties.name[i]}</span>
                    <span className="who-state">
                      {data.counties.state[i]}
                      {compare === i && <span className="compare-mark"> · Compare</span>}
                      {!result.floor[i] && <span className="floor-mark"> · below floor</span>}
                    </span>
                  </span>
                  <span className="score num">{fmtScore(result.comp[i]!)}</span>
                  <PillarStack result={result} i={i} />
                  <span className={`stab${stabilityStale ? " is-stale" : ""}`}>
                    {tiers ? <Barcode tiers={tiers} /> : <span className="barcode-empty" />}
                    <span className="stab-share">
                      {share === undefined || Number.isNaN(share) ? "—" : `Top 10 in ${fmtPct(share)}`}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      )}
      {changes.dropped.length > 0 && (
        <div className="dropped">
          <h3>Left the top {result.topN}</h3>
          <ul>
            {changes.dropped.map((x) => (
              <li key={x.idx}>
                <button className="dropped-btn" onClick={() => onSelect(x.idx)}>
                  <span className="dropped-name">
                    {data.counties.name[x.idx]}, {data.counties.state[x.idx]}
                  </span>
                  <span className="dropped-why">
                    was {x.prevRank} · {x.reason}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {stability && (
        <p className="fine stab-def">
          {stability.warning ??
            `Rank stability: share of ${fmtInt(samples)} weight scenarios, sampled around the stated weights, that rank the county top ${result.topN}. Barcodes show the same ${stability.barcodeSamples} scenarios in order. Dark: top 3. Mid: 4 to 10. Pale: outside.`}
        </p>
      )}
    </section>
  );
}

function Arrow({ up }: { up: boolean }) {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden className="arrow">
      <path d={up ? "M5 1 L9 7 L1 7 Z" : "M5 9 L9 3 L1 3 Z"} fill="currentColor" />
    </svg>
  );
}

export function Barcode({ tiers, tall = false }: { tiers: Uint8Array; tall?: boolean }) {
  const cw = 3;
  const gap = 1;
  const h = tall ? 32 : 18;
  const w = tiers.length * (cw + gap) - gap;
  return (
    <svg className={`barcode${tall ? " is-tall" : ""}`} viewBox={`-1 -1 ${w + 2} ${h + 2}`} preserveAspectRatio="none" aria-hidden>
      <rect x={-0.5} y={-0.5} width={w + 1} height={h + 1} className="barcode-frame" vectorEffect="non-scaling-stroke" />
      {Array.from(tiers, (t, k) => (
        <rect key={k} x={k * (cw + gap)} y={0} width={cw} height={h} className={`bar t${t}`} />
      ))}
    </svg>
  );
}

function PillarStack({ result, i }: { result: RunResult; i: number }) {
  // Each pillar's share of the composite: weight x score over available weight.
  let den = 0;
  for (const p of result.hs.pillars) if (!Number.isNaN(result.hs.pillarScore[p]![i]!)) den += result.weights[p]!;
  return (
    <span className="stack" aria-hidden>
      {result.hs.pillars.map((p) => {
        const s = result.hs.pillarScore[p]![i]!;
        if (Number.isNaN(s) || den === 0) return null;
        const c = (result.weights[p]! * s) / den; // points of composite
        return <span key={p} className="stack-seg" style={{ width: `${c}%`, background: `var(--p-${p}, var(--ink-2))` }} />;
      })}
    </span>
  );
}

function EmptyShortlist({ data, result }: { data: CockpitData; result: RunResult }) {
  const entries = Object.entries(result.gates.failCounts).sort((a, b) => b[1] - a[1]);
  const worst = entries[0];
  const label = worst ? data.gates.find((g) => g.key === worst[0])?.label : null;
  return (
    <div className="empty">
      <p className="empty-title">No county passes these gates.</p>
      {label && (
        <p>
          The strictest gate is <strong>{label}</strong>, which excludes {fmtInt(worst![1])} counties. Relax it in the gate list.
        </p>
      )}
    </div>
  );
}
