import { useMemo } from "react";
import type { CockpitData } from "../data/types";

export interface CountyOption {
  label: string; // "Loudoun, VA (51107)"
  i: number;
}

/** Shared by the map search and the compare picker: one label format, one way to resolve typed text. */
export function useCountyLookup(data: CockpitData) {
  return useMemo(() => {
    const options: CountyOption[] = data.counties.fips.map((f, i) => ({
      label: `${data.counties.name[i]}, ${data.counties.state[i]} (${f})`,
      i,
    }));
    const byLabel = new Map(options.map((o) => [o.label.toLowerCase(), o.i]));
    /** Exact label, then a 5-digit FIPS, then the first label that starts with the text. */
    const resolve = (value: string): number | null => {
      const v = value.trim().toLowerCase();
      if (!v) return null;
      const exact = byLabel.get(v);
      if (exact !== undefined) return exact;
      if (/^\d{5}$/.test(v)) {
        const f = data.counties.fips.indexOf(v);
        if (f >= 0) return f;
      }
      return options.find((o) => o.label.toLowerCase().startsWith(v))?.i ?? null;
    };
    const isExact = (value: string) => byLabel.has(value.toLowerCase());
    return { options, resolve, isExact };
  }, [data]);
}
