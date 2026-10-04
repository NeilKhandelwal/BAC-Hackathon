// URL-addressable cockpit state. A link carries the preset plus only what
// differs from it, so recordings can open at an exact scenario.
//
//   ?preset=balanced&h=2050&s=rcp45&cool=evaporative
//    &w=energy_carbon:30,water:20        weights in percent
//    &g=max_queue_median_age_years:3,exclude_moratorium_state_active:1,max_grid_co2_lb_mwh:off
//    &c=53025&cmp=51107                  selected and comparison county

import type { CockpitData, Conditions, GateValue, Preset } from "../data/types";

export interface ViewState {
  conditions: Conditions;
  selected: string | null;
  compare: string | null;
}

export const DEMO_START = { preset: "balanced" } as const;

export function fromPreset(p: Preset): Conditions {
  return {
    presetId: p.presetId,
    facility: { ...p.facility },
    horizon: p.horizon,
    scenario: p.scenario,
    gates: { ...p.gates },
    weights: { ...p.weights },
    floorPercentile: p.floorPercentile,
    floorExempt: [...p.floorExempt],
  };
}

export function presetOf(data: CockpitData, id: string): Preset {
  return data.presets.find((p) => p.presetId === id) ?? data.presets[0]!;
}

const round = (x: number) => Math.round(x * 1000) / 1000;

export function isEdited(data: CockpitData, c: Conditions): boolean {
  const p = presetOf(data, c.presetId);
  if (c.horizon !== p.horizon || c.scenario !== p.scenario || c.facility.cooling !== p.facility.cooling) return true;
  for (const k of Object.keys(p.weights)) if (round(c.weights[k] ?? 0) !== round(p.weights[k] ?? 0)) return true;
  for (const k of Object.keys(p.gates)) if (c.gates[k] !== p.gates[k]) return true;
  return false;
}

export function encode(data: CockpitData, v: ViewState): string {
  const c = v.conditions;
  const p = presetOf(data, c.presetId);
  const q = new URLSearchParams();
  q.set("preset", c.presetId);
  if (c.horizon !== p.horizon) q.set("h", String(c.horizon));
  if (c.scenario !== p.scenario) q.set("s", c.scenario);
  if (c.facility.cooling !== p.facility.cooling) q.set("cool", c.facility.cooling);
  const w = Object.keys(c.weights)
    .filter((k) => round(c.weights[k] ?? 0) !== round(p.weights[k] ?? 0))
    .map((k) => `${k}:${+((c.weights[k] ?? 0) * 100).toFixed(1)}`);
  if (w.length) q.set("w", w.join(","));
  const g = Object.keys(c.gates)
    .filter((k) => c.gates[k] !== p.gates[k])
    .map((k) => {
      const x = c.gates[k];
      return `${k}:${x === null ? "off" : x === true ? 1 : x === false ? 0 : x}`;
    });
  if (g.length) q.set("g", g.join(","));
  if (v.selected) q.set("c", v.selected);
  if (v.compare) q.set("cmp", v.compare);
  return `?${q.toString().replace(/%3A/g, ":").replace(/%2C/g, ",")}`;
}

/** Parse a query string. Anything unknown or malformed is dropped and reported, never thrown. */
export function decode(data: CockpitData, search: string): { view: ViewState; ignored: string[] } {
  const q = new URLSearchParams(search);
  const ignored: string[] = [];
  const pid = q.get("preset");
  const preset = presetOf(data, pid ?? DEMO_START.preset);
  if (pid && preset.presetId !== pid) ignored.push(`preset "${pid}"`);
  const c = fromPreset(preset);

  const h = q.get("h");
  if (h === "2026" || h === "2050") c.horizon = Number(h) as 2026 | 2050;
  else if (h) ignored.push(`horizon "${h}"`);
  const s = q.get("s");
  if (s === "rcp45" || s === "rcp85") c.scenario = s;
  else if (s) ignored.push(`scenario "${s}"`);
  const cool = q.get("cool");
  if (cool === "dry" || cool === "evaporative" || cool === "hybrid") c.facility.cooling = cool;
  else if (cool) ignored.push(`cooling "${cool}"`);

  for (const part of (q.get("w") ?? "").split(",").filter(Boolean)) {
    const [k, v] = part.split(":");
    const x = Number(v);
    if (k && k in c.weights && Number.isFinite(x) && x >= 0 && x <= 100) c.weights[k] = x / 100;
    else ignored.push(`weight "${part}"`);
  }
  const gateDefs = new Map(data.gates.map((g) => [g.key, g]));
  for (const part of (q.get("g") ?? "").split(",").filter(Boolean)) {
    const i = part.lastIndexOf(":");
    const k = part.slice(0, i);
    const v = part.slice(i + 1);
    const def = gateDefs.get(k);
    if (!def) {
      ignored.push(`gate "${part}"`);
      continue;
    }
    let val: GateValue | undefined;
    if (v === "off") val = def.kind === "flag" ? false : null;
    else if (def.kind === "flag") val = v === "1" ? true : v === "0" ? false : undefined;
    else {
      const x = Number(v);
      if (Number.isFinite(x) && def.range && x >= def.range.min && x <= def.range.max) val = x;
    }
    if (val === undefined) ignored.push(`gate "${part}"`);
    else c.gates[k] = val;
  }

  const fipsSet = new Set(data.counties.fips);
  const pick = (key: string) => {
    const f = q.get(key);
    if (!f) return null;
    if (fipsSet.has(f)) return f;
    ignored.push(`county "${f}"`);
    return null;
  };
  return { view: { conditions: c, selected: pick("c"), compare: pick("cmp") }, ignored };
}
