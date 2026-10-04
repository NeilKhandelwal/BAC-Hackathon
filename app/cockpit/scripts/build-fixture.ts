// Builds the cockpit's static data from the repo:
//   public/data/fixture.json        a CockpitData file with SYNTHETIC county values
//
// Presets, pillar mapping, gate definitions, and county identities are real
// (engine/conditions/*.yaml, engine/pillars.yaml, the geometry file). Every
// county value is generated, with spatial structure so the map reads like a
// plausible country, and the file says so in meta.synthetic.
//
// Run: npm run data:fixture (or npm run data to build both fixture and engine export)

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "yaml";
import { geoArea } from "d3-geo";
import type { FeatureCollection, Geometry } from "geojson";
import type {
  CockpitData,
  Conditions,
  GateDef,
  GateValue,
  MetricDef,
  PillarDef,
  Preset,
  Scenario,
} from "../src/data/types";

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, "../../..");
const out = resolve(here, "../public/data");

// ---------------------------------------------------------------- inputs

type PillarYaml = Record<
  string,
  { column: string; direction: "higher_better" | "lower_better"; transform?: "log1p"; horizon_2050?: string }[]
>;
const pillarsYaml = parse(readFileSync(resolve(repo, "engine/pillars.yaml"), "utf8")) as PillarYaml;
const manifest = JSON.parse(
  readFileSync(resolve(repo, "data/processed/county_features.manifest.json"), "utf8"),
) as { columns_missing?: string[] | Record<string, string> };
const missing = new Set(
  Array.isArray(manifest.columns_missing) ? manifest.columns_missing : Object.keys(manifest.columns_missing ?? {}),
);
type Props = { fips: string; county_name: string; state: string };
const geo = JSON.parse(readFileSync(resolve(repo, "data/processed/counties.geojson"), "utf8")) as FeatureCollection<
  Geometry,
  Props
>;

// ---------------------------------------------------------------- labels

const PILLAR_LABELS: Record<string, [string, string]> = {
  energy_carbon: ["Energy and carbon", "Energy"],
  water: ["Water", "Water"],
  climate_resilience: ["Climate resilience", "Climate"],
  grid_infrastructure: ["Grid and infrastructure", "Grid"],
  land: ["Land", "Land"],
  community: ["Community", "Community"],
  permitting: ["Permitting", "Permitting"],
  cost: ["Cost of power", "Cost"],
};

// column -> [label, unit, source, decimals]
const INFO: Record<string, [string, string, string, number]> = {
  grid_co2_lb_mwh: ["Grid CO2 intensity", "lb/MWh", "EPA eGRID2023", 0],
  grid_renewable_share: ["Grid renewable share", "share", "EPA eGRID2023", 2],
  queue_active_mw_clean_excl_storage: ["Clean generation in queue", "MW", "LBNL Queued Up", 0],
  queue_operational_mw_online_5y: ["Queue capacity delivered, 5 yr", "MW", "LBNL Queued Up", 0],
  wind_speed_100m_ms: ["Wind speed at 100 m", "m/s", "NREL WIND Toolkit", 1],
  plant_clean_capacity_mw_100km: ["Clean plant capacity within 100 km", "MW", "EIA-860", 0],
  drought_share_weeks_d2plus: ["Area in severe drought, mean", "share", "U.S. Drought Monitor", 2],
  nri_drought_score: ["Drought risk", "score", "FEMA NRI", 0],
  water_stress_bws: ["Baseline water stress", "of 5", "WRI Aqueduct 4.0", 1],
  water_stress_2050: ["Water stress 2050", "of 5", "WRI Aqueduct 4.0, BAU", 1],
  cdd_hist: ["Cooling degree days", "°F-days", "CMRA", 0],
  cdd_2050_rcp45: ["Cooling degree days 2050", "°F-days", "CMRA, RCP4.5", 0],
  cdd_2050_rcp85: ["Cooling degree days 2050", "°F-days", "CMRA, RCP8.5", 0],
  nri_inland_flood_score: ["Inland flood risk", "score", "FEMA NRI", 0],
  nri_coastal_flood_score: ["Coastal flood risk", "score", "FEMA NRI", 0],
  nri_wildfire_score: ["Wildfire risk", "score", "FEMA NRI", 0],
  nri_hurricane_score: ["Hurricane risk", "score", "FEMA NRI", 0],
  nri_heat_wave_score: ["Heat wave risk", "score", "FEMA NRI", 0],
  nri_tornado_score: ["Tornado risk", "score", "FEMA NRI", 0],
  nri_winter_score: ["Winter weather risk", "score", "FEMA NRI", 0],
  days_above_95f_hist: ["Days above 95°F", "days/yr", "CMRA", 0],
  days_above_95f_2050_rcp45: ["Days above 95°F 2050", "days/yr", "CMRA, RCP4.5", 0],
  days_above_95f_2050_rcp85: ["Days above 95°F 2050", "days/yr", "CMRA, RCP8.5", 0],
  queue_median_age_years: ["Queue median wait", "yr", "LBNL Queued Up", 1],
  queue_withdrawal_rate: ["Queue withdrawal rate", "share", "LBNL Queued Up", 2],
  fiber_share_locations: ["Locations with fiber", "share", "FCC BDC via Esri", 2],
  dc_existing_count: ["Existing data centers", "count", "FracTracker", 0],
  plant_capacity_mw_100km: ["Plant capacity within 100 km", "MW", "EIA-860", 0],
  coal_retired_mw: ["Retired coal capacity", "MW", "EIA-860", 0],
  pop_density_per_sqkm: ["Population density", "per km²", "Census 2025", 1],
  land_area_sqkm: ["Land area", "km²", "Census Gazetteer", 0],
  heat_sink_score: ["Heat reuse potential", "index", "Derived from CMRA, Census", 0],
  population: ["Population", "people", "Census 2025", 0],
  unemployment_rate_pct_2023: ["Unemployment rate 2023", "%", "BLS LAUS", 1],
  pop_change_pct_since_peak: ["Population change since peak", "%", "Census", 1],
  mfg_emp_share_1969: ["Manufacturing job share, 1969", "share", "BEA", 2],
  industrial_price_cents_kwh: ["Industrial electricity price", "¢/kWh", "EIA-861", 1],
  air_nonattainment_count: ["Air quality nonattainment areas", "count", "EPA Green Book", 0],
  water_permit_risk: ["Water permit risk", "of 3", "State water regime", 0],
  state_policy_risk: ["State policy risk", "of 3", "State policy review", 0],
  pct_developed: ["Developed land", "share", "NLCD", 2],
  pct_cropland: ["Cropland", "share", "NLCD", 2],
  pct_forest_wetland: ["Forest and wetland", "share", "NLCD", 2],
  pct_protected: ["Protected land", "share", "USGS PAD-US", 2],
  tribal_land_share: ["Tribal land", "share", "Census AIANNH", 2],
  moratorium_active: ["County moratorium active", "flag", "FracTracker", 0],
  moratorium_state_active: ["State moratorium active", "flag", "FracTracker", 0],
};

// ---------------------------------------------------------------- synthetic values

function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rand = mulberry32(20261004);
const gauss = () => {
  const u = Math.max(rand(), 1e-9);
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rand());
};
const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));

// A smooth random field over the US: a sum of Gaussian bumps, scaled to 0..1.
function field(bumps = 7) {
  const b = Array.from({ length: bumps }, () => ({
    lat: 25 + rand() * 24,
    lon: -124 + rand() * 57,
    s: 3 + rand() * 9,
    w: rand() * 2 - 0.6,
  }));
  return (lat: number, lon: number) => {
    let v = 0;
    for (const k of b) v += k.w * Math.exp(-((lat - k.lat) ** 2 + ((lon - k.lon) * 0.8) ** 2) / (2 * k.s * k.s));
    return 1 / (1 + Math.exp(-2.2 * v));
  };
}

const n = geo.features.length;
const fips: string[] = [];
const name: string[] = [];
const state: string[] = [];
const lat: number[] = [];
const lon: number[] = [];
const area: number[] = [];
for (const f of geo.features) {
  fips.push(f.properties.fips);
  name.push(f.properties.county_name);
  state.push(f.properties.state);
  // centroid by bounding box midpoint is enough for synthetic fields
  const coords: number[][] = [];
  const walk = (c: unknown): void => {
    if (Array.isArray(c) && typeof c[0] === "number") coords.push(c as number[]);
    else if (Array.isArray(c)) c.forEach(walk);
  };
  walk((f.geometry as { coordinates: unknown }).coordinates);
  const xs = coords.map((c) => c[0]!);
  const ys = coords.map((c) => c[1]!);
  lon.push(+((Math.min(...xs) + Math.max(...xs)) / 2).toFixed(3));
  lat.push(+((Math.min(...ys) + Math.max(...ys)) / 2).toFixed(3));
  area.push(geoArea(f) * 6371 * 6371);
}

const states = [...new Set(state)].sort();
const stateRand = (lo: number, hi: number) => {
  const m = new Map(states.map((s) => [s, lo + rand() * (hi - lo)]));
  return (i: number) => m.get(state[i]!)!;
};
const stateInt = (lo: number, hi: number) => {
  const m = new Map(states.map((s) => [s, Math.floor(lo + rand() * (hi - lo + 1))]));
  return (i: number) => m.get(state[i]!)!;
};
const COASTAL = new Set("TX LA MS AL FL GA SC NC VA MD DE NJ NY CT RI MA NH ME WA OR CA".split(" "));
const GULF_ATL = new Set("TX LA MS AL FL GA SC NC VA MD DE NJ NY CT RI MA".split(" "));

const values: Record<string, (number | null)[]> = {};
const col = (id: string, fn: (i: number) => number | null) => {
  values[id] = Array.from({ length: n }, (_, i) => {
    const v = fn(i);
    return v === null || !Number.isFinite(v) ? null : v;
  });
};
const sometimesNull = (p: number, v: number) => (rand() < p ? null : v);
const lognormal = (mu: number, sigma: number) => Math.exp(mu + sigma * gauss());

const co2 = stateRand(150, 1750);
const price = stateRand(5.5, 19);
const fWind = field();
const fPlant = field(9);
const fFiber = field(8);
const fUrban = field(10);
const fFlood = field(9);
const fQueue = field(8);

col("population", (i) => Math.round(clamp(lognormal(Math.log(9000) + 2.2 * fUrban(lat[i]!, lon[i]!), 1.1), 300, 9.8e6)));
col("land_area_sqkm", (i) => +area[i]!.toFixed(1));
col("pop_density_per_sqkm", (i) => +(values.population![i]! / area[i]!).toFixed(2));
col("grid_co2_lb_mwh", (i) => Math.round(co2(i)));
col("grid_renewable_share", (i) => +clamp(0.95 - co2(i) / 1900 + gauss() * 0.04, 0.02, 0.92).toFixed(3));
col("queue_active_mw_clean_excl_storage", (i) => (rand() < 0.3 ? 0 : Math.round(lognormal(5 + 1.5 * fWind(lat[i]!, lon[i]!), 1.2))));
col("queue_operational_mw_online_5y", () => (rand() < 0.42 ? 0 : Math.round(lognormal(4.2, 1.3))));
col("wind_speed_100m_ms", (i) => +clamp(5 + 3.2 * fWind(lat[i]!, lon[i]!) + (lon[i]! > -105 && lon[i]! < -94 ? 1 : 0) + gauss() * 0.3, 4, 10).toFixed(2));
col("plant_clean_capacity_mw_100km", (i) => Math.round(lognormal(6 + 2.4 * fPlant(lat[i]!, lon[i]!), 0.7)));
col("plant_capacity_mw_100km", (i) => Math.round(values.plant_clean_capacity_mw_100km![i]! * (1.6 + rand() * 2.5)));
col("drought_share_weeks_d2plus", (i) => +clamp((lon[i]! < -100 ? 0.12 : 0.03) + rand() * 0.12, 0, 0.45).toFixed(3));
col("nri_drought_score", (i) => +clamp(values.drought_share_weeks_d2plus![i]! * 180 + gauss() * 10, 0, 100).toFixed(1));
const bws = (i: number) => clamp((lon[i]! < -102 && lat[i]! < 42 ? 3.2 : lon[i]! < -97 ? 1.8 : 0.7) + gauss() * 0.7, 0, 5);
col("water_stress_bws", (i) => +bws(i).toFixed(2));
col("water_stress_2050", (i) => +clamp(values.water_stress_bws![i]! + 0.15 + rand() * 0.7, 0, 5).toFixed(2));
col("cdd_hist", (i) => Math.round(clamp(4200 - (lat[i]! - 25) * 150 + gauss() * 180, 120, 4600)));
col("cdd_2050_rcp45", (i) => Math.round(values.cdd_hist![i]! * (1.18 + rand() * 0.15) + 120));
col("cdd_2050_rcp85", (i) => Math.round(values.cdd_hist![i]! * (1.35 + rand() * 0.3) + 200));
col("hdd_hist", (i) => Math.round(clamp(1000 + (lat[i]! - 25) * 300 + gauss() * 250, 200, 10500)));
col("nri_inland_flood_score", (i) => +clamp(100 * fFlood(lat[i]!, lon[i]!) + gauss() * 14, 0, 100).toFixed(1));
col("nri_coastal_flood_score", (i) => (COASTAL.has(state[i]!) && rand() < 0.35 ? +(rand() * 100).toFixed(1) : 0));
col("nri_wildfire_score", (i) => +clamp((lon[i]! < -104 ? 62 : 22) + gauss() * 18, 0, 100).toFixed(1));
col("nri_hurricane_score", (i) => (GULF_ATL.has(state[i]!) && lat[i]! < 41 ? +clamp(85 - (lat[i]! - 25) * 4 + gauss() * 12, 1, 100).toFixed(1) : 0));
col("nri_heat_wave_score", (i) => +clamp(40 + (36 - Math.abs(lat[i]! - 36)) + gauss() * 15, 0, 100).toFixed(1));
col("nri_tornado_score", (i) => +clamp((lon[i]! > -102 && lon[i]! < -84 && lat[i]! < 42 ? 70 : 30) + gauss() * 15, 0, 100).toFixed(1));
col("nri_winter_score", (i) => +clamp((lat[i]! - 28) * 4 + gauss() * 12, 0, 100).toFixed(1));
col("days_above_95f_hist", (i) => Math.round(clamp((36 - lat[i]!) * 4 + (lon[i]! < -100 ? 18 : 0) + gauss() * 6 + 10, 0, 140)));
col("days_above_95f_2050_rcp45", (i) => Math.round(values.days_above_95f_hist![i]! * 1.4 + 6 + rand() * 6));
col("days_above_95f_2050_rcp85", (i) => Math.round(values.days_above_95f_hist![i]! * 1.8 + 12 + rand() * 10));
col("queue_median_age_years", (i) => sometimesNull(0.18, +clamp(1 + 6 * fQueue(lat[i]!, lon[i]!) + gauss() * 0.9, 0.3, 11).toFixed(2)));
col("queue_withdrawal_rate", () => sometimesNull(0.24, +clamp(0.15 + rand() * 0.6, 0, 1).toFixed(3)));
col("fiber_share_locations", (i) => sometimesNull(0.01, +clamp(fFiber(lat[i]!, lon[i]!) * 0.85 + gauss() * 0.12, 0, 0.98).toFixed(3)));
col("dc_existing_count", (i) => (fips[i] === "51107" ? 160 : rand() < 0.88 ? 0 : Math.round(lognormal(0.8, 1))));
col("coal_retired_mw", () => (rand() < 0.9 ? 0 : Math.round(200 + rand() * 2400)));
col("heat_sink_score", (i) => Math.round(values.hdd_hist![i]! * Math.log1p(values.pop_density_per_sqkm![i]!)));
col("unemployment_rate_pct_2023", () => +clamp(3.6 + gauss() * 1.4, 1.2, 14).toFixed(1));
col("pop_change_pct_since_peak", () => +clamp(-Math.abs(gauss() * 12), -70, 0).toFixed(1));
col("mfg_emp_share_1969", () => sometimesNull(0.04, +clamp(0.18 + gauss() * 0.1, 0, 0.6).toFixed(3)));
col("industrial_price_cents_kwh", (i) => +price(i).toFixed(2));
col("air_nonattainment_count", () => (rand() < 0.9 ? 0 : 1 + Math.floor(rand() * 3)));
const wp = stateInt(1, 3);
const sp = stateInt(1, 3);
col("water_permit_risk", (i) => wp(i));
col("state_policy_risk", (i) => sp(i));
col("pct_developed", (i) => +clamp(0.02 + values.pop_density_per_sqkm![i]! / 900 + rand() * 0.04, 0, 0.95).toFixed(3));
col("pct_cropland", (i) => +clamp((lon[i]! > -104 && lon[i]! < -82 && lat[i]! > 36 ? 0.45 : 0.1) + gauss() * 0.15, 0, 0.95).toFixed(3));
col("pct_forest_wetland", (i) => +clamp((lon[i]! > -95 ? 0.45 : 0.15) + gauss() * 0.15, 0, 0.95).toFixed(3));
col("pct_protected", () => +clamp(rand() < 0.7 ? rand() * 0.04 : rand() * 0.5, 0, 1).toFixed(3));
col("tribal_land_share", () => (rand() < 0.94 ? 0 : +(rand() * 0.8).toFixed(3)));
col("moratorium_active", () => (rand() < 0.012 ? 1 : 0));
const moratoriumStates = new Set(["GA"]);
col("moratorium_state_active", (i) => (moratoriumStates.has(state[i]!) ? 1 : 0));

// ---------------------------------------------------------------- metrics and pillars

const pillars: PillarDef[] = [];
const metrics: MetricDef[] = [];
const seen = new Set<string>();
const missingColumns: string[] = [];
let coverageDenominator = 0;

function addMetric(id: string, pillar: string | null, direction: MetricDef["direction"], extra: Partial<MetricDef> = {}) {
  if (seen.has(id)) return;
  seen.add(id);
  const [label, unit, source, decimals] = INFO[id] ?? [id, "", "unknown", 2];
  metrics.push({ id, label, unit, pillar, direction, kind: "observed", source, decimals, ...extra });
}

for (const [pid, cols] of Object.entries(pillarsYaml)) {
  const [label, short] = PILLAR_LABELS[pid] ?? [pid, pid];
  pillars.push({ id: pid, label, short });
  for (const c of cols) {
    coverageDenominator += 1;
    if (missing.has(c.column) || !values[c.column]) {
      missingColumns.push(c.column);
      continue;
    }
    const horizon2050: Partial<Record<Scenario, string>> | undefined = c.horizon_2050
      ? {
          rcp45: c.horizon_2050.replace("{scenario}", "rcp45"),
          rcp85: c.horizon_2050.replace("{scenario}", "rcp85"),
        }
      : undefined;
    addMetric(c.column, pid, c.direction, { transform: c.transform, horizon2050 });
    for (const fut of Object.values(horizon2050 ?? {})) addMetric(fut, null, c.direction, { kind: "projected" });
  }
}

// ---------------------------------------------------------------- gates

const gates: GateDef[] = [
  { key: "max_queue_median_age_years", label: "Queue median wait at most", column: "queue_median_age_years", kind: "max", unit: "yr", range: { min: 1, max: 10, step: 0.5 }, editable: true },
  { key: "min_nearby_capacity_multiple", label: "Plant capacity within 100 km at least", column: "plant_capacity_mw_100km", kind: "capacity_multiple", unit: "× facility MW", range: { min: 0, max: 20, step: 1 }, editable: true },
  { key: "min_fiber_share_locations", label: "Locations with fiber at least", column: "fiber_share_locations", kind: "min", unit: "share", range: { min: 0, max: 0.8, step: 0.05 }, editable: true },
  { key: "max_grid_co2_lb_mwh", label: "Grid CO2 at most", column: "grid_co2_lb_mwh", kind: "max", unit: "lb/MWh", range: { min: 200, max: 1600, step: 10 }, editable: true },
  { key: "min_renewable_share", label: "Grid renewable share at least", column: "grid_renewable_share", kind: "min", unit: "share", range: { min: 0, max: 0.9, step: 0.05 }, editable: true },
  { key: "max_water_stress_if_evaporative", label: "Water stress at most, if evaporative", column: "water_stress_bws", kind: "evaporative_water", unit: "of 5", range: { min: 0, max: 5, step: 0.5 }, editable: true },
  { key: "min_population", label: "Population at least", column: "population", kind: "min", unit: "people", range: { min: 0, max: 50000, step: 1000 }, editable: true },
  { key: "max_pct_protected", label: "Protected land at most", column: "pct_protected", kind: "max", unit: "share", range: { min: 0, max: 1, step: 0.05 }, editable: true },
  { key: "max_tribal_land_share", label: "Tribal land at most", column: "tribal_land_share", kind: "max", unit: "share", range: { min: 0, max: 1, step: 0.05 }, editable: true },
  { key: "exclude_moratorium_active", label: "Exclude county moratoria", column: "moratorium_active", kind: "flag", unit: "", editable: true },
  { key: "exclude_moratorium_state_active", label: "Exclude state moratoria", column: "moratorium_state_active", kind: "flag", unit: "", editable: true },
  { key: "exclude_air_nonattainment", label: "Exclude air nonattainment", column: "air_nonattainment_count", kind: "flag", unit: "", editable: true },
];
for (const h of ["nri_inland_flood_score", "nri_coastal_flood_score", "nri_wildfire_score", "nri_hurricane_score", "nri_tornado_score"]) {
  const [label] = INFO[h]!;
  gates.push({ key: `hazard_percentile_max.${h}`, label: `${label} below percentile`, column: h, kind: "hazard_pct", unit: "pct", range: { min: 50, max: 100, step: 1 }, editable: true });
}
for (const g of gates) if (!seen.has(g.column)) addMetric(g.column, null, "higher_better");

// ---------------------------------------------------------------- presets

const LABELS: Record<string, string> = {
  balanced: "Balanced",
  speed_to_power: "Speed to power",
  sustainability_first: "Sustainability first",
};
type PresetYaml = {
  name: string;
  description: string;
  facility: { mw: number; online_year: number; cooling: Conditions["facility"]["cooling"] };
  horizon: number;
  scenario: Scenario;
  gates: Record<string, unknown>;
  weights: Record<string, number>;
  pillar_floor_percentile?: number;
  pillar_floor_exempt?: string[];
  robustness?: { samples?: number; concentration?: number; top_n?: number; seed?: number };
};
const presets: Preset[] = ["balanced", "speed_to_power", "sustainability_first"].map((id) => {
  const y = parse(readFileSync(resolve(repo, `engine/conditions/${id}.yaml`), "utf8")) as PresetYaml;
  const g: Record<string, GateValue> = {};
  for (const def of gates) {
    const [head, sub] = def.key.split(".");
    const raw = sub ? (y.gates[head!] as Record<string, unknown> | undefined)?.[sub] : y.gates[head!];
    g[def.key] = typeof raw === "number" || typeof raw === "boolean" ? raw : null;
  }
  return {
    presetId: id,
    label: LABELS[id] ?? id,
    description: y.description.trim(),
    facility: { mw: y.facility.mw, onlineYear: y.facility.online_year, cooling: y.facility.cooling },
    horizon: y.horizon === 2050 ? 2050 : 2026,
    scenario: y.scenario,
    gates: g,
    weights: y.weights,
    floorPercentile: y.pillar_floor_percentile ?? 0,
    floorExempt: y.pillar_floor_exempt ?? [],
    robustness: {
      samples: y.robustness?.samples ?? 2000,
      concentration: y.robustness?.concentration ?? 20,
      topN: y.robustness?.top_n ?? 10,
      seed: y.robustness?.seed ?? 0,
    },
  };
});

// ---------------------------------------------------------------- write

const data: CockpitData = {
  meta: {
    source: "fixture",
    synthetic: true,
    label: "Synthetic county values. Presets, pillar mapping, and county names are real.",
    generatedAt: new Date().toISOString(),
    notes: [
      "Every county value in this file is generated. Do not cite any number from it.",
      "Columns missing from the real table are absent here too, and lower coverage.",
    ],
    nullPolicy: {
      pillarMean: "ignore_null",
      composite: "renormalize_available",
      gate: "unknown_never_fails",
      description: {
        pillar: "A pillar score averages the metrics that have data. Missing metrics are left out of the average.",
        composite: "When a whole pillar has no data, the composite reweights over the pillars that do.",
        gate: "A gate never excludes a county for missing data. It marks the gate as unknown.",
      },
    },
    missingColumns,
    coverageDenominator,
  },
  pillars,
  metrics,
  gates,
  presets,
  counties: { fips, name, state, lat, lon },
  values,
};

mkdirSync(out, { recursive: true });
writeFileSync(resolve(out, "fixture.json"), JSON.stringify(data));
// counties.topo.json comes from scripts/build-geometry.ts, which keeps shared borders intact.
console.log(`fixture: ${n} counties, ${metrics.length} metrics, ${gates.length} gates, ${presets.length} presets`);
console.log(`missing columns: ${missingColumns.join(", ") || "none"}`);
