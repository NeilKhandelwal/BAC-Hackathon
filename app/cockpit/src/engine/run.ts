// One engine run for the UI: conditions in, everything the cockpit shows out.

import type { CockpitData, Conditions, Horizon, PillarId, Scenario } from "../data/types";
import {
  applyGates,
  composite,
  floorOk,
  type GateLog,
  type HorizonScores,
  normalizeWeights,
  order,
  percentileRank,
  scoreHorizon,
  stability,
  type Stability,
  toVec,
  topReasons,
  type Vec,
  WeightsError,
} from "./rank";

export interface RunResult {
  conditions: Conditions;
  hs: HorizonScores;
  weights: Record<PillarId, number>; // normalized over pillars with data
  weightsNote: string | null; // set when the stated weights were renormalized or replaced
  gates: GateLog;
  comp: Vec;
  floor: Uint8Array;
  /** county indices, rank order, gate-passing only */
  ranked: number[];
  /** county index -> 1-based rank among gate-passing counties */
  rankOf: Int32Array;
  /** county index -> rank under the other horizon, same gates; 0 when not ranked */
  rankOther: Int32Array;
  otherHorizon: Horizon;
  passedCount: number;
  floorOkCount: number;
  stability: Stability | null;
  topN: number;
  /** raw national percentile of a hazard column, higher is more hazard; what hazard gates compare */
  hazardPct: (column: string) => Vec;
}

const cache = new Map<string, HorizonScores>();
export function horizonScores(data: CockpitData, h: Horizon, s: Scenario): HorizonScores {
  const key = `${h}:${s}`;
  let hs = cache.get(key);
  if (!hs) {
    hs = scoreHorizon(data, h, s);
    cache.set(key, hs);
  }
  return hs;
}

const hazardCache = new Map<string, Vec>();
function hazardPct(data: CockpitData) {
  return (column: string) => {
    let v = hazardCache.get(column);
    if (!v) {
      // raw national percentile, higher means more hazard
      v = percentileRank(toVec(data.values[column], data.counties.fips.length));
      hazardCache.set(column, v);
    }
    return v;
  };
}

export function resetCaches() {
  cache.clear();
  hazardCache.clear();
}

function weightsFor(c: Conditions, hs: HorizonScores): { w: Record<PillarId, number>; note: string | null } {
  try {
    const w = normalizeWeights(c.weights, hs.pillars);
    const sum = hs.pillars.reduce((a, p) => a + Math.max(0, Number(c.weights[p]) || 0), 0);
    const note = Math.abs(sum - 1) > 0.005 ? `Weights sum to ${(sum * 100).toFixed(0)}%. Scored as shares of the total.` : null;
    return { w, note };
  } catch (e) {
    if (!(e instanceof WeightsError)) throw e;
    const w: Record<PillarId, number> = {};
    for (const p of hs.pillars) w[p] = 1 / hs.pillars.length;
    return { w, note: "Every weight is zero. Scored with equal weights until you set one." };
  }
}

export function run(
  data: CockpitData,
  c: Conditions,
  opts: { topN: number; robustness: { samples: number; concentration: number; seed: number }; withStability: boolean },
): RunResult {
  const hs = horizonScores(data, c.horizon, c.scenario);
  const { w, note } = weightsFor(c, hs);
  const hz = hazardPct(data);
  const gates = applyGates(data, c, hz);
  const comp = composite(hs, w);
  const floor = floorOk(hs, w, c.floorPercentile, c.floorExempt);
  const ranked = order(comp, floor, gates.passed);
  const n = comp.length;
  const rankOf = new Int32Array(n);
  ranked.forEach((i, r) => (rankOf[i] = r + 1));

  const otherHorizon: Horizon = c.horizon === 2050 ? 2026 : 2050;
  const hsO = horizonScores(data, otherHorizon, c.scenario);
  const wO = weightsFor(c, hsO).w;
  const rankedO = order(composite(hsO, wO), floorOk(hsO, wO, c.floorPercentile, c.floorExempt), gates.passed);
  const rankOther = new Int32Array(n);
  rankedO.forEach((i, r) => (rankOther[i] = r + 1));

  let floorOkCount = 0;
  for (const i of ranked) floorOkCount += floor[i]!;

  const st = opts.withStability
    ? stability(hs, w, floor, gates.passed, { ...opts.robustness, topN: opts.topN })
    : null;

  return {
    conditions: c,
    hs,
    weights: w,
    weightsNote: note,
    gates,
    comp,
    floor,
    ranked,
    rankOf,
    rankOther,
    otherHorizon,
    passedCount: ranked.length,
    floorOkCount,
    stability: st,
    topN: opts.topN,
    hazardPct: hz,
  };
}

/** Rank stability for an existing run, so the UI can defer this heavier step. */
export function stabilityFor(
  r: RunResult,
  robustness: { samples: number; concentration: number; seed: number },
): Stability {
  return stability(r.hs, r.weights, r.floor, r.gates.passed, { ...robustness, topN: r.topN });
}

export { topReasons };
