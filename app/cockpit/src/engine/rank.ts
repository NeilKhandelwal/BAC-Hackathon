// Browser port of engine/rank.py. The Python engine is the engine of record;
// this file follows its semantics and should change only when rank.py does.
//
//   gates -> national column percentiles -> pillar means (nulls skipped)
//   -> weighted composite (renormalized over available pillars)
//   -> floor rule on national pillar percentiles -> order
//   -> rank stability by Dirichlet weight draws

import type { CockpitData, Conditions, GateDef, Horizon, MetricDef, PillarId, Scenario } from "../data/types";

export type Vec = Float64Array; // NaN marks a missing value

// ---------------------------------------------------------------- percentiles

/** pandas Series.rank(pct=True, method="average") * 100, ascending. NaN stays NaN. */
export function percentileRank(v: ArrayLike<number>): Vec {
  const n = v.length;
  const idx: number[] = [];
  for (let i = 0; i < n; i++) if (!Number.isNaN(v[i]!)) idx.push(i);
  idx.sort((a, b) => v[a]! - v[b]!);
  const out = new Float64Array(n).fill(NaN);
  const m = idx.length;
  let i = 0;
  while (i < m) {
    let j = i;
    while (j + 1 < m && v[idx[j + 1]!] === v[idx[i]!]) j++;
    const avg = (i + j) / 2 + 1; // 1-based average rank
    for (let k = i; k <= j; k++) out[idx[k]!] = (avg / m) * 100;
    i = j + 1;
  }
  return out;
}

export function toVec(values: (number | null)[] | undefined, n: number): Vec {
  const out = new Float64Array(n).fill(NaN);
  if (!values) return out;
  for (let i = 0; i < n; i++) {
    const x = values[i];
    if (x !== null && x !== undefined) out[i] = x;
  }
  return out;
}

/** Direction-adjusted national percentile, 100 is best. */
export function metricPercentile(raw: Vec, m: Pick<MetricDef, "direction" | "transform">): Vec {
  // Apply the transform even though log1p is mathematically monotonic. At
  // floating-point precision, Python/NumPy can collapse nearly equal raw
  // values into a tie; applying it here preserves pandas average-rank parity.
  const transformed = m.transform === "log1p" ? raw.map((x) => Math.log1p(x)) : raw;
  if (m.direction === "higher_better") return percentileRank(transformed);
  const neg = transformed.map((x) => -x);
  return percentileRank(neg);
}

// ---------------------------------------------------------------- horizon scoring

export interface HorizonScores {
  horizon: Horizon;
  scenario: Scenario;
  /** pillar -> the columns it scores under this horizon */
  columns: Record<PillarId, string[]>;
  /** column -> direction-adjusted national percentile */
  colPct: Record<string, Vec>;
  /** pillar -> mean of its column percentiles, nulls skipped */
  pillarScore: Record<PillarId, Vec>;
  /** pillar -> national percentile of the pillar score, for the floor rule */
  pillarPct: Record<PillarId, Vec>;
  pillars: PillarId[]; // pillars with at least one column
  coverage: Vec;
  /** 2050 columns that replaced today's */
  swapped: string[];
}

export function scoreHorizon(data: CockpitData, horizon: Horizon, scenario: Scenario): HorizonScores {
  const n = data.counties.fips.length;
  const byPillar = new Map<PillarId, MetricDef[]>();
  for (const m of data.metrics) {
    if (!m.pillar) continue;
    byPillar.set(m.pillar, [...(byPillar.get(m.pillar) ?? []), m]);
  }
  const columns: Record<PillarId, string[]> = {};
  const colPct: Record<string, Vec> = {};
  const pillarScore: Record<PillarId, Vec> = {};
  const pillarPct: Record<PillarId, Vec> = {};
  const swapped: string[] = [];
  const pillars: PillarId[] = [];
  const nonNull = new Float64Array(n);

  for (const p of data.pillars) {
    const ms = byPillar.get(p.id) ?? [];
    const cols: string[] = [];
    for (const m of ms) {
      let column = m.id;
      const future = m.horizon2050?.[scenario];
      if (horizon === 2050 && future && data.values[future]) {
        column = future;
        swapped.push(future);
      }
      if (!data.values[column]) continue;
      cols.push(column);
      colPct[column] = metricPercentile(toVec(data.values[column], n), m);
    }
    if (cols.length === 0) continue;
    pillars.push(p.id);
    columns[p.id] = cols;
    const score = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      let s = 0;
      let c = 0;
      for (const col of cols) {
        const x = colPct[col]![i]!;
        if (!Number.isNaN(x)) {
          s += x;
          c++;
        }
      }
      score[i] = c ? s / c : NaN;
      nonNull[i]! += c;
    }
    pillarScore[p.id] = score;
    pillarPct[p.id] = percentileRank(score);
  }
  const coverage = new Float64Array(n);
  const denom = data.meta.coverageDenominator || 1;
  for (let i = 0; i < n; i++) coverage[i] = nonNull[i]! / denom;
  return { horizon, scenario, columns, colPct, pillarScore, pillarPct, pillars, coverage, swapped };
}

// ---------------------------------------------------------------- weights and composite

/** Weights over pillars that have data, renormalized to sum to 1. Throws when no positive weight has data. */
export function normalizeWeights(weights: Record<PillarId, number>, pillars: PillarId[]): Record<PillarId, number> {
  const w: Record<PillarId, number> = {};
  let sum = 0;
  for (const p of pillars) {
    const x = Math.max(0, Number(weights[p]) || 0);
    w[p] = x;
    sum += x;
  }
  if (sum <= 0) throw new WeightsError("no pillar with positive weight has any data");
  for (const p of pillars) w[p] = w[p]! / sum;
  return w;
}

export class WeightsError extends Error {}

export function composite(hs: HorizonScores, w: Record<PillarId, number>): Vec {
  const n = hs.coverage.length;
  const out = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    let num = 0;
    let den = 0;
    for (const p of hs.pillars) {
      const s = hs.pillarScore[p]![i]!;
      if (!Number.isNaN(s)) {
        num += s * w[p]!;
        den += w[p]!;
      }
    }
    out[i] = den > 0 ? num / den : NaN;
  }
  return out;
}

export function floorOk(hs: HorizonScores, w: Record<PillarId, number>, floor: number, exempt: PillarId[]): Uint8Array {
  const n = hs.coverage.length;
  const out = new Uint8Array(n).fill(1);
  const cols = hs.pillars.filter((p) => w[p]! > 0 && !exempt.includes(p));
  if (!floor || cols.length === 0) return out;
  for (let i = 0; i < n; i++) {
    for (const p of cols) {
      const x = hs.pillarPct[p]![i]!;
      if (!Number.isNaN(x) && x < floor) {
        out[i] = 0;
        break;
      }
    }
  }
  return out;
}

/** Floor-passing first, then composite descending; NaN composites last. Returns county indices in rank order. */
export function order(comp: Vec, floor: Uint8Array, passed: Uint8Array): number[] {
  const idx: number[] = [];
  for (let i = 0; i < comp.length; i++) if (passed[i]) idx.push(i);
  return idx.sort((a, b) => {
    if (floor[a] !== floor[b]) return floor[b]! - floor[a]!;
    const ca = comp[a]!;
    const cb = comp[b]!;
    if (Number.isNaN(ca) || Number.isNaN(cb)) return Number.isNaN(ca) ? (Number.isNaN(cb) ? a - b : 1) : -1;
    return cb - ca || a - b;
  });
}

// ---------------------------------------------------------------- gates

export interface GateLog {
  passed: Uint8Array;
  failed: string[][]; // per county, gate keys
  unknown: string[][];
  failCounts: Record<string, number>;
  active: GateDef[];
}

export function gateIsActive(g: GateDef, c: Conditions): boolean {
  const v = c.gates[g.key];
  if (v === null || v === undefined || v === false) return false;
  if (g.kind === "evaporative_water") return c.facility.cooling === "evaporative" || c.facility.cooling === "hybrid";
  return true;
}

export function applyGates(data: CockpitData, c: Conditions, hazardPct: (column: string) => Vec): GateLog {
  const n = data.counties.fips.length;
  const failed: string[][] = Array.from({ length: n }, () => []);
  const unknown: string[][] = Array.from({ length: n }, () => []);
  const failCounts: Record<string, number> = {};
  const active = data.gates.filter((g) => gateIsActive(g, c));

  for (const g of active) {
    const t = c.gates[g.key]!;
    const raw = g.kind === "hazard_pct" ? hazardPct(g.column) : toVec(data.values[g.column], n);
    const thr = typeof t === "number" ? t : 0;
    let count = 0;
    for (let i = 0; i < n; i++) {
      const v = raw[i]!;
      if (Number.isNaN(v)) {
        unknown[i]!.push(g.key);
        continue;
      }
      let fail = false;
      switch (g.kind) {
        case "max":
        case "evaporative_water":
        case "hazard_pct":
          fail = v > thr;
          break;
        case "min":
          fail = v < thr;
          break;
        case "flag":
          fail = v > 0;
          break;
        case "capacity_multiple":
          fail = v < thr * c.facility.mw;
          break;
      }
      if (fail) {
        failed[i]!.push(g.key);
        count++;
      }
    }
    failCounts[g.key] = count;
  }
  const passed = new Uint8Array(n);
  for (let i = 0; i < n; i++) passed[i] = failed[i]!.length === 0 ? 1 : 0;
  return { passed, failed, unknown, failCounts, active };
}

// ---------------------------------------------------------------- rank stability

export interface Stability {
  samples: number;
  topN: number;
  /** per county, draws that rank it in the top 3; NaN when not computed */
  top3: Vec;
  /** per county, draws that rank it in the top N; NaN when not computed */
  topNCount: Vec;
  /** topNCount / samples; NaN when not computed */
  share: Vec;
  warning: string | null;
}

function gammaSample(alpha: number, rnd: () => number, gauss: () => number): number {
  if (alpha < 1) return gammaSample(alpha + 1, rnd, gauss) * Math.pow(rnd(), 1 / alpha);
  const d = alpha - 1 / 3;
  const c = 1 / Math.sqrt(9 * d);
  for (;;) {
    let x: number;
    let v: number;
    do {
      x = gauss();
      v = 1 + c * x;
    } while (v <= 0);
    v = v * v * v;
    const u = rnd();
    if (u < 1 - 0.0331 * x ** 4 || Math.log(u) < 0.5 * x * x + d * (1 - v + Math.log(v))) return d * v;
  }
}

export function mulberry32(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function stability(
  hs: HorizonScores,
  w: Record<PillarId, number>,
  floor: Uint8Array,
  passed: Uint8Array,
  cfg: { samples: number; concentration: number; topN: number; seed: number },
): Stability {
  const n = hs.coverage.length;
  const share = new Float64Array(n).fill(NaN);
  const top3 = new Float64Array(n).fill(NaN);
  const topNCount = new Float64Array(n).fill(NaN);
  const { samples, concentration, topN } = cfg;
  const pos = hs.pillars.filter((p) => w[p]! > 0);
  const eligible: number[] = [];
  for (let i = 0; i < n; i++) {
    if (!passed[i] || !floor[i]) continue;
    if (pos.some((p) => !Number.isNaN(hs.pillarScore[p]![i]!))) eligible.push(i);
  }
  if (samples <= 0 || eligible.length <= topN) {
    return {
      samples,
      topN,
      top3,
      topNCount,
      share,
      warning: `Rank stability not computed: ${eligible.length} counties pass the gates and the floor, not more than ${topN}.`,
    };
  }
  const rnd = mulberry32(cfg.seed + 1);
  const gauss = () => {
    const u = Math.max(rnd(), 1e-12);
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rnd());
  };
  const m = eligible.length;
  const k = pos.length;
  // pillar scores of eligible counties, row-major, NaN kept
  const S = new Float64Array(m * k);
  for (let r = 0; r < m; r++) for (let j = 0; j < k; j++) S[r * k + j] = hs.pillarScore[pos[j]!]![eligible[r]!]!;
  const hits = new Uint32Array(m);
  const hits3 = new Uint32Array(m);
  const comp = new Float64Array(m);
  const top = new Int32Array(topN);
  const topV = new Float64Array(topN);
  const draw = new Float64Array(k);

  for (let s = 0; s < samples; s++) {
    let sum = 0;
    for (let j = 0; j < k; j++) {
      draw[j] = gammaSample(concentration * w[pos[j]!]! * k, rnd, gauss);
      sum += draw[j]!;
    }
    for (let j = 0; j < k; j++) draw[j] = draw[j]! / sum;
    // composite per eligible county under this draw
    for (let r = 0; r < m; r++) {
      let num = 0;
      let den = 0;
      const o = r * k;
      for (let j = 0; j < k; j++) {
        const x = S[o + j]!;
        if (!Number.isNaN(x)) {
          num += x * draw[j]!;
          den += draw[j]!;
        }
      }
      comp[r] = den > 0 ? num / den : -Infinity;
    }
    // top N by insertion into a small sorted buffer
    let filled = 0;
    for (let r = 0; r < m; r++) {
      const v = comp[r]!;
      if (filled < topN) {
        let p = filled++;
        while (p > 0 && topV[p - 1]! < v) {
          topV[p] = topV[p - 1]!;
          top[p] = top[p - 1]!;
          p--;
        }
        topV[p] = v;
        top[p] = r;
      } else if (v > topV[topN - 1]!) {
        let p = topN - 1;
        while (p > 0 && topV[p - 1]! < v) {
          topV[p] = topV[p - 1]!;
          top[p] = top[p - 1]!;
          p--;
        }
        topV[p] = v;
        top[p] = r;
      }
    }
    for (let p = 0; p < topN; p++) {
      if (topV[p] === -Infinity) continue;
      const r = top[p]!;
      hits[r]!++;
      if (p < 3) hits3[r]!++; // the buffer is sorted, so slots 0-2 are ranks 1-3
    }
  }
  // Every eligible county gets counts, including zeros; ineligible ones stay NaN.
  for (let r = 0; r < m; r++) {
    const i = eligible[r]!;
    topNCount[i] = hits[r]!;
    top3[i] = hits3[r]!;
    share[i] = hits[r]! / samples;
  }
  return { samples, topN, top3, topNCount, share, warning: null };
}

// ---------------------------------------------------------------- top reasons

/** Columns adding most above the median, as in rank.py top_reasons. */
export function topReasons(hs: HorizonScores, w: Record<PillarId, number>, i: number, k = 3): string[] {
  const parts: { col: string; v: number }[] = [];
  for (const p of hs.pillars) {
    const cols = hs.columns[p]!;
    const present = cols.filter((c) => !Number.isNaN(hs.colPct[c]![i]!));
    for (const c of present) {
      const v = ((hs.colPct[c]![i]! - 50) / present.length) * w[p]!;
      if (v > 0) parts.push({ col: c, v });
    }
  }
  return parts
    .sort((a, b) => b.v - a.v)
    .slice(0, k)
    .map((x) => x.col);
}
