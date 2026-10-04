import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";
import { parse } from "yaml";
import type { CockpitData, Conditions } from "../src/data/types";
import { labelError, loadTabs, MAX_TABS, storeTabs, toPreset, toTab, type SavedTab } from "../src/state/tabs";
import { customId, decode, encode, fromPreset, isEdited } from "../src/state/url";
import { toYaml, yamlFileName } from "../src/state/yaml";

const data = JSON.parse(readFileSync(new URL("../public/data/engine-export.json", import.meta.url), "utf8")) as CockpitData;
const withTabs = (tabs: SavedTab[]): CockpitData => ({ ...data, presets: [...data.presets, ...tabs.map((t) => toPreset(data, t))] });

/** A scenario a user could reach with the controls: balanced, then five edits. */
function edited(): Conditions {
  const c = fromPreset(data.presets.find((p) => p.presetId === "balanced")!);
  c.weights = { ...c.weights, water: 0.4, cost: 0 };
  c.gates = { ...c.gates, max_queue_median_age_years: 3, exclude_moratorium_state_active: true, min_fiber_share_locations: null };
  c.facility = { ...c.facility, cooling: "evaporative" };
  c.horizon = 2050;
  return c;
}
const scenario = (c: Conditions) => ({ ...c, presetId: "" });

describe("custom tabs", () => {
  it("a saved tab reopens as exactly the scenario that was saved", () => {
    const c = edited();
    const p = toPreset(data, toTab(data, "Wet and patient", c));
    expect(scenario(fromPreset(p))).toEqual(scenario(c));
    expect(p.presetId).toBe(customId("Wet and patient"));
    expect(p.label).toBe("Wet and patient");
    expect(p.base).toBe("balanced");
    // rank stability settings come from the base, so the tab's stability shares are comparable to it
    expect(p.robustness).toEqual(data.presets.find((x) => x.presetId === "balanced")!.robustness);
  });

  it("selecting a saved tab is not an edit, and changing it is", () => {
    const all = withTabs([toTab(data, "Wet and patient", edited())]);
    const c = fromPreset(all.presets.at(-1)!);
    expect(isEdited(all, c)).toBe(false);
    expect(isEdited(all, { ...c, weights: { ...c.weights, land: 0.3 } })).toBe(true);
  });

  it("a tab's link opens the same scenario in a browser that never saved the tab", () => {
    const tab = toTab(data, "Wet and patient", edited());
    const all = withTabs([tab]);
    const link = encode(all, { conditions: fromPreset(all.presets.at(-1)!), selected: "53025", compare: null });
    expect(link).toContain("preset=balanced");
    expect(link).not.toContain("custom");

    const elsewhere = decode(data, link);
    expect(elsewhere.ignored).toEqual([]);
    expect(elsewhere.unsavedTab).toBe("Wet and patient");
    expect(elsewhere.view.conditions).toEqual({ ...edited(), presetId: "balanced" });
    expect(elsewhere.view.selected).toBe("53025");

    const here = decode(all, link);
    expect(here.unsavedTab).toBeNull();
    expect(here.view.conditions.presetId).toBe(customId("Wet and patient"));
  });

  it("a tab saved from an edited custom tab still rests on a built-in preset", () => {
    const all = withTabs([toTab(data, "First", edited())]);
    const c = { ...fromPreset(all.presets.at(-1)!), horizon: 2026 as const };
    const second = toPreset(data, toTab(all, "Second", c));
    expect(second.base).toBe("balanced");
    expect(scenario(fromPreset(second))).toEqual(scenario(c));
  });

  it("rejects a name that is empty or already a tab", () => {
    const all = withTabs([toTab(data, "Mine", edited())]);
    expect(labelError(all, "   ")).toMatch(/name/);
    expect(labelError(all, "balanced")).toMatch(/already exists/);
    expect(labelError(all, " mine ")).toMatch(/already exists/);
    expect(labelError(all, "Cheap and clean")).toBeNull();
  });
});

describe("tab storage", () => {
  const stub = (initial: string | null, setItem = vi.fn()) =>
    vi.stubGlobal("window", { localStorage: { getItem: () => initial, setItem } });
  afterEach(() => vi.unstubAllGlobals());

  it("keeps what it stored", () => {
    let kept: string | null = null;
    stub(null, vi.fn((_k: string, v: string) => void (kept = v)));
    const tabs = [toTab(data, "Mine", edited())];
    expect(storeTabs(tabs)).toBe(true);
    stub(kept);
    expect(loadTabs()).toEqual(tabs);
  });

  it("starts with no tabs when storage is corrupt, and caps what it loads", () => {
    stub("{not json");
    expect(loadTabs()).toEqual([]);
    stub(JSON.stringify([{ label: 3 }, "x", null]));
    expect(loadTabs()).toEqual([]);
    stub(JSON.stringify(Array.from({ length: 9 }, (_, i) => ({ label: `t${i}`, query: "?preset=balanced" }))));
    expect(loadTabs()).toHaveLength(MAX_TABS);
  });

  it("drops stored tabs that would duplicate a name or break the name rules", () => {
    const q = "?preset=balanced";
    stub(JSON.stringify([{ label: "Mine", query: q }, { label: "mine", query: q }, { label: " padded ", query: q }, { label: "", query: q }, { label: "x".repeat(40), query: q }]));
    expect(loadTabs()).toEqual([{ label: "Mine", query: q }]);
  });

  it("reports a browser that refuses storage instead of throwing", () => {
    stub(null, vi.fn(() => {
      throw new Error("quota");
    }));
    expect(storeTabs([])).toBe(false);
  });
});

// The download has to mean the same thing to the Python engine as the scenario
// on screen. The committed preset files are the reference for the format.
describe("conditions file", () => {
  type EngineYaml = {
    facility: { mw: number; online_year: number; cooling: string };
    horizon: number;
    scenario: string;
    gates: Record<string, unknown>;
    weights: Record<string, number>;
    pillar_floor_percentile: number;
    pillar_floor_exempt: string[];
    robustness: { samples: number; concentration: number; top_n: number };
  };
  const gate = (y: EngineYaml, key: string) => {
    const [head, sub] = key.split(".");
    return (sub ? (y.gates[head!] as Record<string, unknown> | undefined)?.[sub] : y.gates[head!]) ?? null;
  };

  for (const p of data.presets) {
    it(`an unedited ${p.presetId} downloads as the engine's own ${p.presetId}.yaml`, () => {
      const ours = parse(toYaml(data, fromPreset(p), p.label, p.robustness)) as EngineYaml;
      const theirs = parse(readFileSync(new URL(`../../../engine/conditions/${p.presetId}.yaml`, import.meta.url), "utf8")) as EngineYaml;
      expect(ours.facility).toEqual({ mw: theirs.facility.mw, online_year: theirs.facility.online_year, cooling: theirs.facility.cooling });
      expect(ours.horizon).toBe(theirs.horizon);
      expect(ours.scenario).toBe(theirs.scenario);
      for (const g of data.gates) expect([g.key, gate(ours, g.key)]).toEqual([g.key, gate(theirs, g.key)]);
      expect(ours.weights).toEqual(theirs.weights);
      expect(ours.pillar_floor_percentile).toBe(theirs.pillar_floor_percentile);
      expect(ours.pillar_floor_exempt).toEqual(theirs.pillar_floor_exempt);
      expect(ours.robustness).toMatchObject(theirs.robustness);
    });
  }

  it("carries every edit, and writes a switched-off gate as null or false", () => {
    const y = parse(toYaml(data, edited(), 'Wet: "patient"', data.presets[0]!.robustness)) as EngineYaml & { name: string };
    expect(y.name).toBe('Wet: "patient"');
    expect(y.facility.cooling).toBe("evaporative");
    expect(y.horizon).toBe(2050);
    expect(y.weights.water).toBe(0.4);
    expect(y.weights.cost).toBe(0);
    expect(y.gates.max_queue_median_age_years).toBe(3);
    expect(y.gates.exclude_moratorium_state_active).toBe(true);
    expect(y.gates.min_fiber_share_locations).toBeNull();
  });

  it("names the file after the tab", () => {
    expect(yamlFileName("Cheap & clean (edited)")).toBe("cheap_clean_edited.yaml");
    expect(yamlFileName("???")).toBe("scenario.yaml");
  });
});
