import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { CockpitData } from "../src/data/types";
import { percentileRank, normalizeWeights, WeightsError } from "../src/engine/rank";
import { run } from "../src/engine/run";
import { decode, encode, fromPreset } from "../src/state/url";
import { outcomesOf } from "../src/components/OutcomeBar";

const data = JSON.parse(readFileSync(new URL("../public/data/engine-export.json", import.meta.url), "utf8")) as CockpitData;
const opts = { topN: 10, robustness: { samples: 2000, concentration: 20, seed: 0 }, withStability: true };

describe("percentileRank", () => {
  it("matches pandas average ranks and keeps nulls", () => {
    const r = percentileRank(Float64Array.from([10, 20, 20, NaN, 40]));
    expect(Array.from(r)).toEqual([25, 62.5, 62.5, NaN, 100]);
  });
});

describe("weights", () => {
  it("renormalizes and rejects all-zero", () => {
    expect(normalizeWeights({ a: 2, b: 2 }, ["a", "b"])).toEqual({ a: 0.5, b: 0.5 });
    expect(() => normalizeWeights({ a: 0 }, ["a"])).toThrow(WeightsError);
  });
});

describe("run on the engine export", () => {
  const c = fromPreset(data.presets[0]!);
  const t0 = performance.now();
  const r = run(data, c, opts);
  const ms = performance.now() - t0;

  it("ranks only gate-passing counties, floor-passing first", () => {
    expect(r.passedCount).toBeGreaterThan(10);
    expect(r.passedCount).toBeLessThan(data.counties.fips.length);
    for (const i of r.ranked) expect(r.gates.passed[i]).toBe(1);
    const firstFail = r.ranked.findIndex((i) => !r.floor[i]);
    if (firstFail >= 0) for (const i of r.ranked.slice(firstFail)) expect(r.floor[i]).toBe(0);
  });

  it("never fails a gate on a null value", () => {
    const col = data.values.queue_median_age_years!;
    const nullIdx = col.findIndex((v) => v === null);
    expect(nullIdx).toBeGreaterThanOrEqual(0);
    expect(r.gates.failed[nullIdx]).not.toContain("max_queue_median_age_years");
    expect(r.gates.unknown[nullIdx]).toContain("max_queue_median_age_years");
  });

  it("counts top-3 and top-10 outcomes across every draw", () => {
    const st = r.stability!;
    expect(st.warning).toBeNull();
    expect("tiers" in st).toBe(false); // the first-64 barcode sample is gone
    let n3 = 0;
    let nN = 0;
    for (let i = 0; i < st.share.length; i++) {
      const t3 = st.top3[i]!;
      const tn = st.topNCount[i]!;
      if (Number.isNaN(tn)) {
        expect(Number.isNaN(t3)).toBe(true);
        continue;
      }
      expect(t3).toBeGreaterThanOrEqual(0);
      expect(t3).toBeLessThanOrEqual(tn); // top 3 is a subset of top 10
      expect(tn).toBeLessThanOrEqual(st.samples);
      expect(st.share[i]).toBeCloseTo(tn / st.samples, 12);
      const o = outcomesOf(st, i)!;
      expect(o.top3 + o.ranks4to10 + o.outside).toBe(st.samples); // the three outcomes cover every draw
      expect(Math.min(o.top3, o.ranks4to10, o.outside)).toBeGreaterThanOrEqual(0);
      const pct = [o.top3, o.ranks4to10, o.outside].map((x) => (x / o.samples) * 100);
      expect(pct.reduce((a, b) => a + b, 0)).toBeCloseTo(100, 9); // segments total 100%
      n3 += t3;
      nN += tn;
    }
    // each draw fills exactly 3 top-3 slots and 10 top-10 slots
    expect(n3).toBe(3 * st.samples);
    expect(nN).toBe(10 * st.samples);
    for (const i of r.ranked.slice(0, 10)) expect(outcomesOf(st, i)).not.toBeNull();
    // 2,000 draws, 10 slots each
    let total = 0;
    r.stability!.share.forEach((x) => (total += Number.isNaN(x) ? 0 : x));
    expect(total).toBeCloseTo(10, 5);
  });

  it("is deterministic", () => {
    const again = run(data, c, opts);
    expect(again.ranked.slice(0, 10)).toEqual(r.ranked.slice(0, 10));
    expect(Array.from(again.stability!.share.slice(0, 50))).toEqual(Array.from(r.stability!.share.slice(0, 50)));
  });

  it("runs fast enough to recompute on input", () => {
    console.log(`full run with 2,000 draws: ${ms.toFixed(0)} ms`);
    expect(ms).toBeLessThan(1500);
  });

  it("degrades when gates exclude everything", () => {
    const strict = { ...c, gates: { ...c.gates, min_population: 50000, max_grid_co2_lb_mwh: 200, min_fiber_share_locations: 0.8 } };
    const rs = run(data, strict, opts);
    expect(rs.stability?.warning).toMatch(/not computed/);
  });

  it("treats all-zero weights as equal weights with a note", () => {
    const zero = { ...c, weights: Object.fromEntries(Object.keys(c.weights).map((k) => [k, 0])) };
    const rz = run(data, zero, opts);
    expect(rz.weightsNote).toMatch(/equal weights/);
    expect(rz.ranked.length).toBe(r.ranked.length);
  });
});

describe("url state", () => {
  it("round-trips a scenario and ignores junk", () => {
    const { view } = decode(data, "?preset=speed_to_power&h=2050&w=water:40&g=max_queue_median_age_years:4,exclude_moratorium_state_active:0&c=51107");
    expect(view.conditions.horizon).toBe(2050);
    expect(view.conditions.weights.water).toBeCloseTo(0.4);
    expect(view.conditions.gates.max_queue_median_age_years).toBe(4);
    expect(view.selected).toBe("51107");
    const again = decode(data, encode(data, view)).view;
    expect(again).toEqual(view);
    const bad = decode(data, "?preset=nope&h=3000&w=water:-5&g=bogus:1&c=00000");
    expect(bad.ignored.length).toBe(5);
    expect(bad.view.conditions.presetId).toBe("balanced");
  });
});

describe("rank change summary", () => {
  it("reports counties that left even when the rest keep their order", async () => {
    const { computeChanges } = await import("../src/state/changes");
    const c = fromPreset(data.presets[0]!);
    const a = run(data, c, { ...opts, withStability: false });
    // Keep only the current top 3: the survivors hold their order, seven drop out.
    const keep = new Set(a.ranked.slice(0, 3));
    const b = { ...a, ranked: a.ranked.slice(0, 3), gates: { ...a.gates, passed: a.gates.passed.map((_, i) => (keep.has(i) ? 1 : 0)) as Uint8Array, failed: a.gates.failed.map((f, i) => (keep.has(i) ? f : ["min_population"])) } };
    const ch = computeChanges(data, a, b, 10);
    expect(ch.dropped.length).toBe(7);
    expect(ch.summary).toBe("7 left");
  });
});

describe("outcome bar numbers", () => {
  it("prints percentages that add to exactly 100.0", async () => {
    const { percentParts } = await import("../src/components/OutcomeBar");
    for (const [a, b, c] of [[1959, 41, 0], [667, 667, 666], [1, 1, 1998], [0, 0, 2000], [2000, 0, 0], [333, 1, 1666]] as const) {
      const p = percentParts({ samples: 2000, top3: a, ranks4to10: b, outside: c });
      expect(Math.round(p.reduce((x, y) => x + y, 0) * 10)).toBe(1000);
      p.forEach((x, k) => expect(Math.abs(x - ([a, b, c][k]! / 2000) * 100)).toBeLessThanOrEqual(0.1));
    }
  });

  it("never rounds a partial share to 100% or 0%", async () => {
    const { topNLabel } = await import("../src/components/OutcomeBar");
    expect(topNLabel(2000, 2000, 10)).toBe("Top 10 in 100%");
    expect(topNLabel(1999, 2000, 10)).toBe("Top 10 in >99%");
    expect(topNLabel(1, 2000, 10)).toBe("Top 10 in <1%");
    expect(topNLabel(0, 2000, 10)).toBe("Top 10 in 0%");
    expect(topNLabel(1960, 2000, 10)).toBe("Top 10 in 98%");
  });
});
