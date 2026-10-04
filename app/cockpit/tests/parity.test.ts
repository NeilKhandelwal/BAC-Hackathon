import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { CockpitData, Preset } from "../src/data/types";
import { topReasons } from "../src/engine/rank";
import { resetCaches, run } from "../src/engine/run";
import { fromPreset } from "../src/state/url";

type CsvRow = Record<string, string>;
type EngineReport = {
  passed: number;
  floor_ok: number;
  gate_failures: Record<string, number>;
};

const data = JSON.parse(
  readFileSync(new URL("../public/data/engine-export.json", import.meta.url), "utf8"),
) as CockpitData;

function csvRows(presetId: string): CsvRow[] {
  const text = readFileSync(new URL(`../../../results/${presetId}.csv`, import.meta.url), "utf8").trim();
  const [header, ...lines] = text.split(/\r?\n/);
  const names = header!.split(",");
  return lines.map((line) => Object.fromEntries(names.map((name, i) => [name, line.split(",")[i] ?? ""])));
}

function report(presetId: string): EngineReport {
  return JSON.parse(
    readFileSync(new URL(`../../../results/${presetId}_report.json`, import.meta.url), "utf8"),
  ) as EngineReport;
}

function expectRounded(actual: number, expected: string, label: string) {
  expect(actual, label).toBeCloseTo(Number(expected), 2);
}

function checkPreset(preset: Preset) {
  resetCaches();
  const expectedRows = csvRows(preset.presetId);
  const expectedReport = report(preset.presetId);
  const result = run(data, fromPreset(preset), {
    topN: preset.robustness.topN,
    robustness: preset.robustness,
    withStability: false,
  });

  expect(data.meta.synthetic).toBe(false);
  expect(data.meta.source).toBe("engine");
  expect(result.passedCount).toBe(expectedReport.passed);
  expect(result.floorOkCount).toBe(expectedReport.floor_ok);
  expect(result.ranked.map((i) => data.counties.fips[i])).toEqual(expectedRows.map((row) => row.fips));

  const nonzeroGateFailures = Object.fromEntries(Object.entries(result.gates.failCounts).filter(([, n]) => n > 0));
  expect(nonzeroGateFailures).toEqual(expectedReport.gate_failures);

  // Full rank-order parity above makes the test sensitive to every gate,
  // floor, percentile, and composite calculation. Check detailed values for
  // the displayed shortlist as a more legible diagnosis if semantics drift.
  for (const [rank, row] of expectedRows.slice(0, 10).entries()) {
    const i = result.ranked[rank]!;
    const fips = data.counties.fips[i]!;
    expect(result.floor[i] === 1, `${preset.presetId} ${fips} floor_ok`).toBe(row.floor_ok === "True");
    expectRounded(result.comp[i]!, row.composite!, `${preset.presetId} ${fips} composite`);
    expectRounded(result.hs.coverage[i]!, row.coverage!, `${preset.presetId} ${fips} coverage`);

    for (const pillar of result.hs.pillars) {
      expectRounded(
        result.hs.pillarScore[pillar]![i]!,
        row[`pillar_${pillar}`]!,
        `${preset.presetId} ${fips} ${pillar}`,
      );
    }

    expect(topReasons(result.hs, result.weights, i).join(";")).toBe(row.top_reasons);
    expect(result.gates.failed[i]!.join(";")).toBe(row.failed_gates);
    expect(new Set(result.gates.unknown[i])).toEqual(new Set((row.unknown_gates ?? "").split(";").filter(Boolean)));

    const rank2026 = preset.horizon === 2026 ? result.rankOf[i]! : result.rankOther[i]!;
    const rank2050 = preset.horizon === 2050 ? result.rankOf[i]! : result.rankOther[i]!;
    expect(rank2050 - rank2026).toBe(Number(row.rank_delta_2050));
  }
}

describe("React engine parity with Python reference outputs", () => {
  for (const preset of data.presets) {
    it(`${preset.label}: gates, floor, full ranking, and shortlist scores match`, () => checkPreset(preset));
  }

  it("covers every shipped US preset", () => {
    expect(data.presets.map((preset) => preset.presetId).sort()).toEqual([
      "balanced",
      "speed_to_power",
      "sustainability_first",
    ]);
  });
});

// Robustness is deliberately outside exact parity: Python uses NumPy's random
// generator while the dependency-free browser uses Mulberry32. Both implement
// the same Dirichlet model and are tested for invariants in engine.test.ts, but
// individual Monte Carlo samples are not expected to be bit-identical.
