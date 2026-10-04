import { useLayoutEffect, useRef } from "react";
import type { CockpitData } from "../data/types";
import type { RunResult } from "../engine/run";
import type { Stability } from "../engine/rank";
import type { RankChanges } from "../state/changes";
import { fmtInt, fmtScore } from "../lib/format";
import { CATEGORIES, OutcomeBar, outcomesOf, topNLabel } from "./OutcomeBar";

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
      </div>
      <StabilityLegend stability={stability} topN={result.topN} />
      {top.length === 0 ? (
        <EmptyShortlist data={data} result={result} />
      ) : (
        <ol className="rows" ref={listRef}>
          {top.map((i, r) => {
            const d = changes.delta.get(i);
            const isNew = changes.entered.has(i);
            const o = outcomesOf(stability, i);
            const name = `${data.counties.name[i]}, ${data.counties.state[i]}`;
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
                </button>
                <span className={`stab${stabilityStale ? " is-stale" : ""}`}>
                  {o ? (
                    <OutcomeBar o={o} county={name} above={r >= 6} onActivate={() => onSelect(i)} />
                  ) : (
                    <span className={`outcome-empty${stability ? "" : " is-pending"}`} aria-hidden />
                  )}
                  <span className={`stab-share${o ? "" : " is-muted"}`}>
                    {o ? topNLabel(o.top3 + o.ranks4to10, o.samples, result.topN) : stability ? "Not computed" : "Computing"}
                  </span>
                </span>
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

function StabilityLegend({ stability, topN }: { stability: Stability | null; topN: number }) {
  if (stability?.warning) return <p className="stab-legend fine">{stability.warning}</p>;
  return (
    <p className="stab-legend">
      <span className="stab-legend-title">
        Rank stability
        {stability ? ` · rank in ${fmtInt(stability.samples)} weight scenarios` : ""}
      </span>
      <span className="stab-legend-keys">
        {CATEGORIES.map((c) => (
          <span key={c.key} className="stab-key">
            <span className={`outcome-sw ${c.cls}`} aria-hidden />
            {c.key === "outside" ? `Outside top ${topN}` : c.key === "ranks4to10" ? `Ranks 4–${topN}` : c.label}
          </span>
        ))}
      </span>
    </p>
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
