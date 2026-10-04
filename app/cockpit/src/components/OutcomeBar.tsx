import { useEffect, useId, useRef, useState } from "react";
import type { Stability } from "../engine/rank";
import { fmtInt } from "../lib/format";

/** A county's outcomes across every sampled weight scenario. Counts always sum to `samples`. */
export interface Outcomes {
  samples: number;
  top3: number;
  ranks4to10: number;
  outside: number;
}

export function outcomesOf(st: Stability | null, i: number): Outcomes | null {
  if (!st) return null;
  const t3 = st.top3[i];
  const tn = st.topNCount[i];
  if (t3 === undefined || tn === undefined || Number.isNaN(t3) || Number.isNaN(tn)) return null;
  return { samples: st.samples, top3: t3, ranks4to10: tn - t3, outside: st.samples - tn };
}

export const CATEGORIES = [
  { key: "top3", label: "Top 3", cls: "o-top3" },
  { key: "ranks4to10", label: "Ranks 4–10", cls: "o-top10" },
  { key: "outside", label: "Outside top 10", cls: "o-out" },
] as const;

/**
 * Percentages to one decimal that add up to exactly 100.0, by largest
 * remainder. Rounding each share alone can print 98.0% + 2.1%.
 */
export function percentParts(o: Outcomes): [number, number, number] {
  const counts = [o.top3, o.ranks4to10, o.outside];
  const tenths = counts.map((c) => (c / o.samples) * 1000);
  const floors = tenths.map(Math.floor);
  let left = 1000 - floors.reduce((a, b) => a + b, 0);
  const order = tenths.map((t, k) => [t - floors[k]!, k] as const).sort((a, b) => b[0] - a[0]);
  for (const [, k] of order) {
    if (left <= 0) break;
    floors[k]!++;
    left--;
  }
  return floors.map((t) => t / 10) as [number, number, number];
}

/** "Top 10 in 98%", never rounding a partial share up to 100% or down to 0%. */
export function topNLabel(count: number, samples: number, topN: number): string {
  const p = (count / samples) * 100;
  const shown = count === samples ? "100%" : count === 0 ? "0%" : p > 99.5 ? ">99%" : p < 0.5 ? "<1%" : `${Math.round(p)}%`;
  return `Top ${topN} in ${shown}`;
}


function Segments({ o }: { o: Outcomes }) {
  return (
    <span className="outcome-track" aria-hidden>
      {CATEGORIES.map((c) =>
        o[c.key] > 0 ? <span key={c.key} className={`outcome-seg ${c.cls}`} style={{ flexGrow: o[c.key] }} /> : null,
      )}
    </span>
  );
}

/** The three outcome counts as a small table: used in the tooltip and the finding panel. */
export function OutcomeTable({ o }: { o: Outcomes }) {
  const parts = percentParts(o);
  return (
    <table className="outcome-table">
      <caption>Rank across {fmtInt(o.samples)} weight scenarios</caption>
      <tbody>
        {CATEGORIES.map((c, k) => (
          <tr key={c.key}>
            <th scope="row">
              <span className={`outcome-sw ${c.cls}`} aria-hidden />
              {c.label}
            </th>
            <td className="num">{fmtInt(o[c.key])}</td>
            <td className="num">{parts[k]!.toFixed(1)}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Static bar with no interaction, for places that print the counts beside it. */
export function OutcomeBarStatic({ o }: { o: Outcomes }) {
  return (
    <span className="outcome outcome-lg">
      <Segments o={o} />
    </span>
  );
}

interface Props {
  o: Outcomes;
  county: string;
  /** open the tooltip above the bar, for rows near the bottom of the list */
  above?: boolean;
  /** a click on the bar keeps the row's click behavior */
  onActivate?: () => void;
}

/**
 * Interactive outcome bar. The whole bar is one button: hover, keyboard focus,
 * or a tap shows the tooltip. A tap or Enter also selects the county, as a
 * click on the row always has. Escape or a tap elsewhere closes it.
 */
export function OutcomeBar({ o, county, above = false, onActivate }: Props) {
  const id = useId();
  const wrap = useRef<HTMLSpanElement>(null);
  const [hover, setHover] = useState(false);
  const [focus, setFocus] = useState(false);
  const [pinned, setPinned] = useState(false);
  const open = hover || focus || pinned;

  useEffect(() => {
    if (!pinned) return;
    const off = (e: PointerEvent) => {
      if (!wrap.current?.contains(e.target as Node)) setPinned(false);
    };
    document.addEventListener("pointerdown", off);
    return () => document.removeEventListener("pointerdown", off);
  }, [pinned]);

  return (
    <span
      ref={wrap}
      className="outcome-wrap"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <button
        type="button"
        className="outcome"
        aria-label={`Rank stability for ${county}: ${topNLabel(o.top3 + o.ranks4to10, o.samples, 10).toLowerCase()} of ${fmtInt(o.samples)} weight scenarios`}
        aria-describedby={id}
        aria-expanded={open}
        onFocus={() => setFocus(true)}
        onBlur={() => {
          setFocus(false);
          setPinned(false);
        }}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setPinned(false);
            setFocus(false);
            setHover(false);
          }
        }}
        onClick={() => {
          setPinned(true);
          onActivate?.();
        }}
      >
        <Segments o={o} />
      </button>
      <span role="tooltip" id={id} className={`outcome-tip${above ? " is-above" : ""}`} hidden={!open}>
        <OutcomeTable o={o} />
      </span>
    </span>
  );
}
