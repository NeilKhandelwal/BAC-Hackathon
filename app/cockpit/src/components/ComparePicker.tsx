import { useEffect, useId, useRef, useState } from "react";
import type { CockpitData } from "../data/types";
import type { RunResult } from "../engine/run";
import { useCountyLookup } from "../lib/countyLookup";

const LOUDOUN = "51107";

interface Props {
  data: CockpitData;
  result: RunResult;
  /** the county the finding panel shows */
  idx: number;
  compare: number | null;
  onCompare: (i: number | null) => void;
}

interface Pick {
  i: number;
  title: string;
  note: string;
}

/**
 * "Compare with…" for the finding panel: quick picks for the current leader
 * and the Loudoun benchmark, plus a search over every county.
 */
export function ComparePicker({ data, result, idx, compare, onCompare }: Props) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const wrap = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const popId = useId();
  const inputId = useId();
  const { resolve, isExact } = useCountyLookup(data);

  const name = (i: number) => `${data.counties.name[i]}, ${data.counties.state[i]}`;

  // The leader changes with every scenario; when the viewed county is the
  // leader, the runner-up is the useful comparison.
  const picks: Pick[] = [];
  const [first, second] = result.ranked;
  if (first !== undefined && first !== idx) picks.push({ i: first, title: `#1 · ${name(first)}`, note: "Top of the current ranking" });
  else if (second !== undefined) picks.push({ i: second, title: `#2 · ${name(second)}`, note: "Runner-up in the current ranking" });
  const loudoun = data.counties.fips.indexOf(LOUDOUN);
  if (loudoun >= 0 && loudoun !== idx)
    picks.push({ i: loudoun, title: name(loudoun), note: "Industry benchmark: where data centers already cluster" });

  const close = (refocus: boolean) => {
    setOpen(false);
    setQ("");
    setError(null);
    if (refocus) trigger.current?.focus();
  };

  const choose = (i: number) => {
    if (i === idx) {
      setError("That's the county you're viewing. Pick a different one.");
      return;
    }
    onCompare(i);
    close(true);
  };

  // Close on a press outside, or when focus leaves the picker.
  useEffect(() => {
    if (!open) return;
    const off = (e: PointerEvent) => {
      if (!wrap.current?.contains(e.target as Node)) close(false);
    };
    document.addEventListener("pointerdown", off);
    wrap.current?.querySelector<HTMLElement>(".pick-btn, input")?.focus();
    return () => document.removeEventListener("pointerdown", off);
  }, [open]);

  const submit = (value: string) => {
    const i = resolve(value);
    if (i === null) setError(value.trim() ? "No county matches. Try a name or a 5-digit FIPS." : "Type a county name or FIPS.");
    else choose(i);
  };

  return (
    <div
      className="compare"
      ref={wrap}
      onKeyDown={(e) => {
        if (e.key === "Escape" && open) {
          e.stopPropagation();
          close(true);
        }
      }}
      onBlur={(e) => {
        if (open && !wrap.current?.contains(e.relatedTarget as Node | null)) close(false);
      }}
    >
      <button
        ref={trigger}
        type="button"
        className={`btn btn-quiet compare-trigger${compare !== null ? " is-on" : ""}`}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? popId : undefined}
        onClick={() => (open ? close(false) : setOpen(true))}
      >
        {compare !== null ? (
          <>
            <svg className="compare-swatch" viewBox="0 0 16 12" width="16" height="12" aria-hidden>
              <rect x="1" y="1" width="14" height="10" />
            </svg>
            <span className="compare-label">vs {name(compare)}</span>
          </>
        ) : (
          "Compare with…"
        )}
        <svg className="compare-caret" viewBox="0 0 10 10" width="10" height="10" aria-hidden>
          <path d="M2 3.5 L5 6.5 L8 3.5" />
        </svg>
      </button>

      {open && (
        <div className="compare-pop" id={popId} role="dialog" aria-label={`Compare ${name(idx)} with another county`}>
          {picks.length > 0 && (
            <>
              <p className="compare-h">Quick picks</p>
              <ul className="pick-list">
                {picks.map((p) => (
                  <li key={p.i}>
                    <button type="button" className="pick-btn" aria-pressed={compare === p.i} onClick={() => choose(p.i)}>
                      <span className="pick-title">{p.title}</span>
                      <span className="pick-note">{p.note}</span>
                      {compare === p.i && <span className="pick-current">Current</span>}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
          <form
            className="compare-search"
            onSubmit={(e) => {
              e.preventDefault();
              submit(q);
            }}
          >
            <label htmlFor={inputId} className="compare-h">
              Any county
            </label>
            <div className="compare-row">
              <input
                id={inputId}
                list="county-options"
                placeholder="County name or FIPS"
                value={q}
                aria-invalid={error !== null}
                aria-describedby={error ? `${inputId}-err` : undefined}
                onChange={(e) => {
                  setQ(e.target.value);
                  setError(null);
                  if (isExact(e.target.value)) submit(e.target.value);
                }}
              />
              <button type="submit" className="btn">
                Compare
              </button>
            </div>
            {error && (
              <p id={`${inputId}-err`} className="compare-err" role="alert">
                {error}
              </p>
            )}
          </form>
          {compare !== null && (
            <button
              type="button"
              className="link compare-stop"
              onClick={() => {
                onCompare(null);
                close(true);
              }}
            >
              Stop comparing
            </button>
          )}
        </div>
      )}
    </div>
  );
}
