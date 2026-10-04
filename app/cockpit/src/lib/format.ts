import type { MetricDef } from "../data/types";

const nf = (d: number) => new Intl.NumberFormat("en-US", { maximumFractionDigits: d, minimumFractionDigits: d });

export function fmtInt(x: number): string {
  return nf(0).format(x);
}

export function fmtScore(x: number): string {
  return Number.isNaN(x) ? "No data" : nf(1).format(x);
}

export function fmtPct(share: number, d = 0): string {
  return `${nf(d).format(share * 100)}%`;
}

export function ordinal(x: number): string {
  const r = Math.round(x);
  const s = r % 100 >= 11 && r % 100 <= 13 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[r % 10] ?? "th";
  return `${r}${s}`;
}

/** An observed value with its unit, or "No data". */
export function fmtValue(v: number | null | undefined, m: Pick<MetricDef, "unit" | "decimals">): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "No data";
  if (m.unit === "share") return fmtPct(v, 0);
  if (m.unit === "flag") return v > 0 ? "Yes" : "No";
  if (m.unit === "%") return `${nf(m.decimals).format(v)}%`;
  const num = nf(m.decimals).format(v);
  return m.unit && m.unit !== "count" && m.unit !== "score" && m.unit !== "index" ? `${num} ${m.unit}` : num;
}

export function fmtThreshold(v: number, unit: string): string {
  if (unit === "share") return fmtPct(v, 0);
  if (unit === "pct") return ordinal(v);
  if (unit === "people") return fmtInt(v);
  return `${nf(Number.isInteger(v) ? 0 : 1).format(v)} ${unit}`.trim();
}
