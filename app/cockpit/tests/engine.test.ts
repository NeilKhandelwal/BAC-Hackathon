import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { CockpitData } from "../src/data/types";
import { percentileRank, normalizeWeights, WeightsError } from "../src/engine/rank";
import { run } from "../src/engine/run";
import { decode, encode, fromPreset } from "../src/state/url";

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

  it("computes stability shares and 64-cell barcodes for the top 10", () => {
    expect(r.stability?.warning).toBeNull();
    for (const i of r.ranked.slice(0, 10)) {
      const s = r.stability!.share[i]!;
      expect(s).toBeGreaterThanOrEqual(0);
      expect(s).toBeLessThanOrEqual(1);
      expect(r.stability!.tiers.get(i)?.length).toBe(64);
    }
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
