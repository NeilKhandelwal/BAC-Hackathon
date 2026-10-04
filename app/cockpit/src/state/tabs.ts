// Custom tabs: scenarios a user names and keeps beside the built-in presets.
// A tab is stored as the scenario part of a link, a built-in preset plus what
// differs from it, so a saved tab and a shared link can't drift apart.

import type { CockpitData, Conditions } from "../data/types";
import { customId, decode, presetOf, queryString, scenarioParams, type CustomPreset } from "./url";

export interface SavedTab {
  label: string;
  query: string;
}

const KEY = "cockpit.tabs.v1";
export const MAX_TABS = 4;
export const MAX_LABEL = 24;

/** Tabs kept in this browser. Anything unreadable is dropped, never thrown. */
export function loadTabs(): SavedTab[] {
  try {
    const raw: unknown = JSON.parse(window.localStorage.getItem(KEY) ?? "[]");
    if (!Array.isArray(raw)) return [];
    const seen = new Set<string>();
    return raw
      .filter((t): t is SavedTab => typeof t?.label === "string" && typeof t?.query === "string")
      .filter((t) => {
        const k = t.label.toLowerCase();
        const ok = t.label.trim() === t.label && k !== "" && t.label.length <= MAX_LABEL && !seen.has(k);
        seen.add(k);
        return ok;
      })
      .slice(0, MAX_TABS);
  } catch {
    return [];
  }
}

/** Returns false when the browser refuses storage, so the caller can say the tab won't survive a reload. */
export function storeTabs(tabs: SavedTab[]): boolean {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(tabs));
    return true;
  } catch {
    return false;
  }
}

/** The tab as a preset, so the rest of the cockpit treats it like a built-in one. `data` holds built-in presets only. */
export function toPreset(data: CockpitData, t: SavedTab): CustomPreset {
  const c = decode(data, t.query).view.conditions;
  const base = presetOf(data, c.presetId);
  return {
    ...base,
    ...c,
    presetId: customId(t.label),
    label: t.label,
    description: `Custom tab, saved from ${base.label}.`,
    base: base.presetId,
  };
}

export function toTab(data: CockpitData, label: string, c: Conditions): SavedTab {
  return { label, query: queryString(scenarioParams(data, c)) };
}

/** Why a name can't be used, or null when it can. */
export function labelError(data: CockpitData, label: string): string | null {
  const name = label.trim();
  if (!name) return "Give the tab a name.";
  if (name.length > MAX_LABEL) return `Use ${MAX_LABEL} characters or fewer.`;
  const taken = data.presets.some((p) => p.label.toLowerCase() === name.toLowerCase());
  return taken ? `A tab named "${name}" already exists.` : null;
}
