// Writes the current scenario as a conditions file for the Python engine, in
// the format of engine/conditions/*.yaml. See docs/conditions.md.

import type { CockpitData, Conditions, GateValue, Preset } from "../data/types";

const scalar = (v: GateValue) => (v === null ? "null" : String(v));

export function toYaml(data: CockpitData, c: Conditions, name: string, robustness: Preset["robustness"]): string {
  const lines = [
    "# Saved from the site selection cockpit. Run it with the engine:",
    "#   python -m engine rank --conditions <this file> \\",
    "#     --features data/processed/county_features.parquet --out results/<name>.csv",
    `name: ${JSON.stringify(name)}`,
    "",
    "facility:",
    `  mw: ${c.facility.mw}`,
    `  online_year: ${c.facility.onlineYear}`,
    `  cooling: ${c.facility.cooling}`,
    "",
    `horizon: ${c.horizon}`,
    `scenario: ${c.scenario}`,
    "",
    "gates:",
  ];
  // Dotted keys such as hazard_percentile_max.nri_wildfire_score nest one level.
  const nested = new Map<string, string[]>();
  for (const g of data.gates) {
    const [head, sub] = g.key.split(".");
    const v = scalar(c.gates[g.key] ?? null);
    if (!sub) lines.push(`  ${head}: ${v}`);
    else nested.set(head!, [...(nested.get(head!) ?? []), `    ${sub}: ${v}`]);
  }
  for (const [head, subs] of nested) lines.push(`  ${head}:`, ...subs);
  lines.push("", "weights:");
  for (const p of data.pillars) lines.push(`  ${p.id}: ${c.weights[p.id] ?? 0}`);
  lines.push(
    "",
    `pillar_floor_percentile: ${c.floorPercentile}`,
    `pillar_floor_exempt: [${c.floorExempt.join(", ")}]`,
    "",
    "robustness:",
    `  samples: ${robustness.samples}`,
    `  concentration: ${robustness.concentration}`,
    `  top_n: ${robustness.topN}`,
    `  seed: ${robustness.seed}`,
    "",
  );
  return lines.join("\n");
}

export const yamlFileName = (name: string) =>
  `${name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "scenario"}.yaml`;
