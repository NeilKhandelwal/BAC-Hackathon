import { useState } from "react";
import type { CockpitData, Conditions, GateDef, GateValue } from "../data/types";
import type { RunResult } from "../engine/run";
import { fmtInt, fmtThreshold } from "../lib/format";

interface Props {
  data: CockpitData;
  conditions: Conditions;
  result: RunResult;
  onWeight: (pillar: string, w: number) => void;
  onGate: (key: string, v: GateValue) => void;
}

export function Controls({ data, conditions: c, result, onWeight, onGate }: Props) {
  const stated = data.pillars.reduce((a, p) => a + (c.weights[p.id] ?? 0), 0);
  const hazards = data.gates.filter((g) => g.kind === "hazard_pct");
  const others = data.gates.filter((g) => g.kind !== "hazard_pct");
  const [hazOpen, setHazOpen] = useState(false);
  const hazActive = hazards.filter((g) => c.gates[g.key] !== null);
  const hazExcl = hazards.reduce((a, g) => a + (result.gates.failCounts[g.key] ?? 0), 0);

  return (
    <aside className="rail" aria-label="Weights and gates">
      <section className="weights" aria-labelledby="weights-h">
        <div className="rail-head">
          <h2 id="weights-h">Pillar weights</h2>
          <span className="rail-meta">{Math.round(stated * 100)}% stated</span>
        </div>
        {result.weightsNote && <p className="note">{result.weightsNote}</p>}
        <ul className="weight-list">
          {data.pillars.map((p) => {
            const v = c.weights[p.id] ?? 0;
            const used = result.weights[p.id];
            const id = `w-${p.id}`;
            return (
              <li key={p.id} className="weight" style={{ "--hue": `var(--p-${p.id}, var(--ink-2))` } as React.CSSProperties}>
                <label htmlFor={id} className="weight-label">
                  <span className="swatch" aria-hidden />
                  {p.label}
                </label>
                <output htmlFor={id} className="weight-val">
                  {Math.round(v * 100)}%
                  {used !== undefined && Math.abs(used - v) > 0.005 && <span className="weight-used"> ({Math.round(used * 100)}% used)</span>}
                </output>
                <input
                  id={id}
                  type="range"
                  min={0}
                  max={50}
                  step={1}
                  value={Math.round(v * 100)}
                  onChange={(e) => onWeight(p.id, Number(e.target.value) / 100)}
                  style={{ "--fill": `${(Math.min(v, 0.5) / 0.5) * 100}%` } as React.CSSProperties}
                />
              </li>
            );
          })}
        </ul>
      </section>

      <section className="gates" aria-labelledby="gates-h">
        <div className="rail-head">
          <h2 id="gates-h">Hard gates</h2>
        </div>
        <p className="funnel" aria-live="polite">
          <strong>{fmtInt(result.passedCount)}</strong> of {fmtInt(data.counties.fips.length)} counties pass
        </p>
        <ul className="gate-list">
          {others.map((g) => (
            <GateRow key={g.key} g={g} c={c} count={result.gates.failCounts[g.key]} onGate={onGate} />
          ))}
          <li className="gate-group">
            <button className="gate-group-toggle" aria-expanded={hazOpen} onClick={() => setHazOpen((o) => !o)}>
              <span>Hazard caps ({hazActive.length} on)</span>
              <span className="gate-count">{hazExcl ? `−${fmtInt(hazExcl)}` : "0"}</span>
            </button>
            {hazOpen && (
              <ul className="gate-list nested">
                {hazards.map((g) => (
                  <GateRow key={g.key} g={g} c={c} count={result.gates.failCounts[g.key]} onGate={onGate} />
                ))}
              </ul>
            )}
          </li>
        </ul>
        <p className="fine">Counts overlap: a county can fail more than one gate. Missing data never fails a gate.</p>
      </section>
    </aside>
  );
}

function GateRow({ g, c, count, onGate }: { g: GateDef; c: Conditions; count: number | undefined; onGate: (k: string, v: GateValue) => void }) {
  const v = c.gates[g.key];
  const on = v !== null && v !== false && v !== undefined;
  const inapplicable = g.kind === "evaporative_water" && c.facility.cooling === "dry";
  const id = `g-${g.key}`;
  const fallback = g.range ? (g.range.min + g.range.max) / 2 : 0;

  if (g.kind === "flag") {
    return (
      <li className="gate">
        <label className="gate-check">
          <input type="checkbox" checked={on} onChange={(e) => onGate(g.key, e.target.checked)} />
          <span>{g.label}</span>
        </label>
        <span className="gate-count">{on ? `−${fmtInt(count ?? 0)}` : "off"}</span>
      </li>
    );
  }
  return (
    <li className={`gate${on ? "" : " is-off"}${inapplicable ? " is-na" : ""}`}>
      <div className="gate-top">
        <label className="gate-check">
          <input
            type="checkbox"
            checked={on}
            onChange={(e) => onGate(g.key, e.target.checked ? fallback : null)}
            aria-label={`${g.label}: ${on ? "on" : "off"}`}
          />
          <span>{g.label}</span>
        </label>
        <span className="gate-count">{inapplicable ? "n/a" : on ? `−${fmtInt(count ?? 0)}` : "off"}</span>
      </div>
      {on && g.range && typeof v === "number" && (
        <div className="gate-slider">
          <input
            id={id}
            type="range"
            min={g.range.min}
            max={g.range.max}
            step={g.range.step}
            value={v}
            aria-label={g.label}
            onChange={(e) => onGate(g.key, Number(e.target.value))}
          />
          <output htmlFor={id}>{fmtThreshold(v, g.unit)}</output>
        </div>
      )}
      {inapplicable && <p className="fine">Applies to evaporative or hybrid cooling only.</p>}
    </li>
  );
}
