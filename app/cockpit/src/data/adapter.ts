// The only module that knows where data comes from. The UI imports types and
// loadCockpit(); it never reads files or columns directly.

import type { Topology } from "topojson-specification";
import type { CockpitData } from "./types";

// The engine export is preferred when it exists; the synthetic fixture is the fallback.
const SOURCES = ["data/engine-export.json", "data/fixture.json"];

export class DataError extends Error {}

function check(d: unknown): CockpitData {
  const x = d as CockpitData;
  const fail = (what: string) => {
    throw new DataError(`Data file is missing ${what}.`);
  };
  if (!x || typeof x !== "object") fail("its top-level object");
  if (!x.meta || typeof x.meta.synthetic !== "boolean") fail("meta.synthetic");
  if (!x.meta.nullPolicy?.description) fail("meta.nullPolicy");
  if (!Array.isArray(x.pillars) || x.pillars.length === 0) fail("pillars");
  if (!Array.isArray(x.metrics)) fail("metrics");
  if (!Array.isArray(x.gates)) fail("gates");
  if (!Array.isArray(x.presets) || x.presets.length === 0) fail("presets");
  const n = x.counties?.fips?.length ?? 0;
  if (n === 0) fail("counties");
  for (const [col, v] of Object.entries(x.values ?? {})) {
    if (v.length !== n) throw new DataError(`Column ${col} has ${v.length} values for ${n} counties.`);
  }
  return x;
}

export async function loadCockpit(): Promise<CockpitData> {
  let lastError: unknown = null;
  for (const url of SOURCES) {
    try {
      const r = await fetch(url);
      if (!r.ok || !(r.headers.get("content-type") ?? "").includes("json")) continue;
      return check(await r.json());
    } catch (e) {
      lastError = e;
    }
  }
  throw lastError instanceof DataError ? lastError : new DataError("No data file found. Run npm run data.");
}

export async function loadGeometry(): Promise<Topology> {
  const r = await fetch("data/counties.topo.json");
  if (!r.ok) throw new DataError("County geometry not found. Run npm run data.");
  return (await r.json()) as Topology;
}
