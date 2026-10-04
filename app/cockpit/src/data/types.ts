// The contract between the data export and the cockpit. The fixture
// generator and the future engine export both produce a CockpitData file.

export type Horizon = 2026 | 2050;
export type Scenario = "rcp45" | "rcp85";
export type Direction = "higher_better" | "lower_better";

// Which of the four kinds of number a metric is. See DESIGN.md.
export type MetricKind = "observed" | "projected";

export type PillarId = string;

export interface PillarDef {
  id: PillarId;
  label: string;
  short: string;
}

export interface MetricDef {
  id: string; // column name in the county table
  label: string;
  unit: string; // printed after the value; "" for unitless
  pillar: PillarId | null; // null for gate-only or context columns
  direction: Direction;
  transform?: "log1p";
  kind: MetricKind;
  source: string;
  decimals: number;
  // Columns that replace this one under the 2050 horizon, per scenario.
  horizon2050?: Partial<Record<Scenario, string>>;
}

// One gate as the engine names it in a conditions file.
export type GateKind =
  | "max" // fails where value > threshold
  | "min" // fails where value < threshold
  | "flag" // fails where value > 0 when enabled
  | "hazard_pct" // fails where national percentile of the hazard > threshold
  | "capacity_multiple" // fails where value < threshold * facility.mw
  | "evaporative_water"; // max, applied only to evaporative or hybrid cooling

export interface GateDef {
  key: string; // engine key, e.g. "max_queue_median_age_years" or "hazard_percentile_max.nri_wildfire_score"
  label: string;
  column: string;
  kind: GateKind;
  unit: string;
  // Control range for threshold gates. Flags have none.
  range?: { min: number; max: number; step: number };
  editable: boolean;
}

export type GateValue = number | boolean | null;

export interface Conditions {
  presetId: string;
  facility: { mw: number; onlineYear: number; cooling: "dry" | "evaporative" | "hybrid" };
  horizon: Horizon;
  scenario: Scenario;
  gates: Record<string, GateValue>; // keyed by GateDef.key; null disables
  weights: Record<PillarId, number>;
  floorPercentile: number;
  floorExempt: PillarId[];
}

export interface Preset extends Conditions {
  label: string;
  description: string;
  robustness: { samples: number; concentration: number; topN: number; seed: number };
}

// How the engine treats missing values. The UI prints these descriptions;
// it never writes its own claim about null handling.
export interface NullPolicy {
  pillarMean: "ignore_null";
  composite: "renormalize_available";
  gate: "unknown_never_fails";
  description: { pillar: string; composite: string; gate: string };
}

export interface DataMeta {
  source: "fixture" | "engine";
  synthetic: boolean;
  label: string; // shown in the data badge's detail
  generatedAt: string;
  notes: string[];
  nullPolicy: NullPolicy;
  // Columns listed in the pillar mapping but absent from the table. They
  // count toward the coverage denominator, as in engine/rank.py.
  missingColumns: string[];
  coverageDenominator: number;
}

export interface CountyColumns {
  fips: string[];
  name: string[];
  state: string[];
  lat: number[];
  lon: number[];
}

export interface CockpitData {
  meta: DataMeta;
  pillars: PillarDef[];
  metrics: MetricDef[];
  gates: GateDef[];
  presets: Preset[];
  counties: CountyColumns;
  // Column name to one value per county, aligned with counties.fips.
  values: Record<string, (number | null)[]>;
}
