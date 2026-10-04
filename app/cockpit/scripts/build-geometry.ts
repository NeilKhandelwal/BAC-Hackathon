// Builds public/data/counties.topo.json with shared county borders.
//
// The county GeoJSON in data/processed is simplified one county at a time,
// so neighbors no longer share edges: borders drawn from it come out broken.
// This script builds the topology from full-resolution Census polygons first,
// then simplifies arcs, so each shared border stays one line.
//
// Run: npm run geometry   (needs data/raw/census/cb_2025_us_county_500k.zip and the repo .venv)

import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { topology } from "topojson-server";
import { presimplify, quantile, simplify } from "topojson-simplify";
import { mesh, quantize } from "topojson-client";
import type { FeatureCollection } from "geojson";
import type { GeometryCollection, Topology } from "topojson-specification";

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, "../../..");
const out = resolve(here, "../public/data/counties.topo.json");
const tmp = join(mkdtempSync(join(tmpdir(), "cockpit-geo-")), "counties.geojson");

execFileSync(resolve(repo, ".venv/bin/python"), [resolve(here, "export_geometry.py"), tmp], { stdio: "inherit" });
const geo = JSON.parse(readFileSync(tmp, "utf8")) as FeatureCollection;

// Census cartographic boundaries share exact vertices along borders, so the
// unquantized topology already joins neighbors. Quantize only at the end:
// simplifying a quantized topology keeps every point.
// The simplify typings disagree on property types, so the pipeline runs untyped.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let t: any = topology({ counties: geo });
t = presimplify(t);
// quantile(p) returns the weight that keeps the top p of points by visual
// importance. Keep 3%; shared borders stay shared.
t = simplify(t, quantile(t, 0.03));
// Delta-encode at about 60 m resolution so the file stays small.
const topo = quantize(t, 1e5) as Topology;

// Check: the outside edge should be a small number of rings, not interior fragments.
const obj = topo.objects.counties as GeometryCollection;
const outside = mesh(topo, obj, (a, b) => a === b).coordinates.length;
const fips = new Set(obj.geometries.map((g) => (g.properties as { fips: string }).fips));
const table = JSON.parse(readFileSync(resolve(here, "../public/data/engine-export.json"), "utf8")) as {
  counties: { fips: string[] };
};
const missing = table.counties.fips.filter((f) => !fips.has(f));
if (missing.length) throw new Error(`geometry lacks ${missing.length} counties in the data: ${missing.slice(0, 5).join(", ")}`);

writeFileSync(out, JSON.stringify(topo));
const kb = (JSON.stringify(topo).length / 1024).toFixed(0);
console.log(`counties.topo.json: ${obj.geometries.length} counties, ${topo.arcs.length} arcs, ${outside} outside-edge lines, ${kb} KB`);
