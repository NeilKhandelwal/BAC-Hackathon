import type { CockpitData, Conditions, Horizon, Scenario } from "../data/types";
import { fmtInt } from "../lib/format";

interface Props {
  data: CockpitData;
  conditions: Conditions;
  edited: boolean;
  onPreset: (id: string) => void;
  onHorizon: (h: Horizon) => void;
  onScenario: (s: Scenario) => void;
  onCooling: (c: Conditions["facility"]["cooling"]) => void;
  onReset: () => void;
}

export function TopBar({ data, conditions: c, edited, onPreset, onHorizon, onScenario, onCooling, onReset }: Props) {
  const onTabKey = (e: React.KeyboardEvent<HTMLButtonElement>, i: number) => {
    const n = data.presets.length;
    const next = e.key === "ArrowRight" ? (i + 1) % n : e.key === "ArrowLeft" ? (i - 1 + n) % n : -1;
    if (next < 0) return;
    e.preventDefault();
    onPreset(data.presets[next]!.presetId);
    (e.currentTarget.parentElement?.children[next] as HTMLElement | undefined)?.focus();
  };

  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-name">Site Selection Cockpit</span>
        <span className="brand-sub">{fmtInt(data.counties.fips.length)} US counties</span>
      </div>

      <div className="presets" role="tablist" aria-label="Scenario preset">
        {data.presets.map((p, i) => {
          const active = p.presetId === c.presetId;
          return (
            <button
              key={p.presetId}
              role="tab"
              aria-selected={active}
              tabIndex={active ? 0 : -1}
              className="preset-tab"
              onClick={() => onPreset(p.presetId)}
              onKeyDown={(e) => onTabKey(e, i)}
              title={p.description}
            >
              {p.label}
              {active && edited && <span className="edited">Edited</span>}
            </button>
          );
        })}
      </div>

      <div className="facility" aria-label="Facility">
        <span className="fact">
          <span className="fact-v">{fmtInt(c.facility.mw)} MW</span>
          <span className="fact-k">IT load</span>
        </span>
        <span className="fact">
          <span className="fact-v">{c.facility.onlineYear}</span>
          <span className="fact-k">online</span>
        </span>
        <label className="fact fact-select">
          <select value={c.facility.cooling} onChange={(e) => onCooling(e.target.value as Conditions["facility"]["cooling"])}>
            <option value="dry">Dry</option>
            <option value="hybrid">Hybrid</option>
            <option value="evaporative">Evaporative</option>
          </select>
          <span className="fact-k">cooling</span>
        </label>
      </div>

      <div className="horizon">
        <div className="segmented" role="radiogroup" aria-label="Horizon">
          {([2026, 2050] as Horizon[]).map((h) => (
            <button key={h} role="radio" aria-checked={c.horizon === h} onClick={() => onHorizon(h)}>
              {h === 2026 ? "Today" : "2050"}
            </button>
          ))}
        </div>
        <label className="scenario" aria-disabled={c.horizon !== 2050}>
          <span className="visually-hidden">Emissions scenario</span>
          <select value={c.scenario} disabled={c.horizon !== 2050} onChange={(e) => onScenario(e.target.value as Scenario)}>
            <option value="rcp85">RCP8.5</option>
            <option value="rcp45">RCP4.5</option>
          </select>
        </label>
      </div>

      <div className="topbar-end">
        <span className={`badge-data ${data.meta.synthetic ? "is-synthetic" : "is-engine"}`} title={data.meta.label}>
          {data.meta.synthetic ? "Synthetic data" : "Real engine data"}
        </span>
        <button className="btn" onClick={onReset}>
          Reset demo
        </button>
      </div>
    </header>
  );
}
