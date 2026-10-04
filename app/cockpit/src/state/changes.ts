// What changed between two runs, in words the shortlist can print.

import type { CockpitData, Conditions } from "../data/types";
import type { RunResult } from "../engine/run";
import { fmtThreshold } from "../lib/format";

export interface Dropped {
  idx: number;
  prevRank: number;
  reason: string;
}

export interface RankChanges {
  cause: string | null;
  /** county index -> places moved up (positive) or down (negative) */
  delta: Map<number, number>;
  entered: Set<number>;
  dropped: Dropped[];
  summary: string | null;
}

export const NO_CHANGES: RankChanges = { cause: null, delta: new Map(), entered: new Set(), dropped: [], summary: null };

/** One short phrase naming what the user changed. */
export function describeCause(data: CockpitData, a: Conditions, b: Conditions): string {
  if (a.presetId !== b.presetId) return `Preset: ${data.presets.find((p) => p.presetId === b.presetId)?.label ?? b.presetId}`;
  if (a.horizon !== b.horizon) return `Horizon: ${b.horizon === 2050 ? "2050" : "Today"}`;
  if (a.scenario !== b.scenario) return `Scenario: ${b.scenario === "rcp45" ? "RCP4.5" : "RCP8.5"}`;
  if (a.facility.cooling !== b.facility.cooling) return `Cooling: ${b.facility.cooling}`;
  for (const p of data.pillars) {
    if ((a.weights[p.id] ?? 0) !== (b.weights[p.id] ?? 0))
      return `${p.label} weight ${Math.round((b.weights[p.id] ?? 0) * 100)}%`;
  }
  for (const g of data.gates) {
    const v = b.gates[g.key];
    if (a.gates[g.key] !== v) {
      if (v === null || v === false) return `Gate off: ${g.label}`;
      if (v === true) return `Gate on: ${g.label}`;
      return typeof v === "number" ? `${g.label} ${fmtThreshold(v, g.unit)}` : `Gate changed: ${g.label}`;
    }
  }
  return "Conditions changed";
}

export function gateLabel(data: CockpitData, key: string): string {
  return data.gates.find((g) => g.key === key)?.label ?? key;
}

export function computeChanges(data: CockpitData, prev: RunResult, next: RunResult, topN: number): RankChanges {
  const before = prev.ranked.slice(0, topN);
  const after = next.ranked.slice(0, topN);
  const beforeRank = new Map(before.map((i, r) => [i, r + 1]));
  const delta = new Map<number, number>();
  const entered = new Set<number>();
  after.forEach((i, r) => {
    const was = beforeRank.get(i);
    if (was === undefined) entered.add(i);
    else if (was !== r + 1) delta.set(i, was - (r + 1));
  });
  const afterSet = new Set(after);
  const dropped: Dropped[] = [];
  before.forEach((i, r) => {
    if (afterSet.has(i)) return;
    let reason: string;
    if (!next.gates.passed[i]) reason = `Excluded: ${gateLabel(data, next.gates.failed[i]![0]!)}`;
    else if (!next.floor[i] && prev.floor[i]) reason = "Now below a pillar floor";
    else reason = `Now rank ${next.rankOf[i]}`;
    dropped.push({ idx: i, prevRank: r + 1, reason });
  });
  const moved = delta.size;
  const cause = describeCause(data, prev.conditions, next.conditions);
  const summary =
    entered.size === 0 && moved === 0
      ? "Top 10 unchanged"
      : [entered.size ? `${entered.size} new` : null, moved ? `${moved} moved` : null].filter(Boolean).join(", ");
  return { cause, delta, entered, dropped, summary };
}
