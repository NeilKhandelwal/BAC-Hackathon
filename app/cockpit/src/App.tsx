import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Topology } from "topojson-specification";
import { loadCockpit, loadGeometry } from "./data/adapter";
import type { CockpitData, Conditions, GateValue } from "./data/types";
import { run, stabilityFor, type RunResult } from "./engine/run";
import type { Stability } from "./engine/rank";
import { computeChanges, NO_CHANGES, type RankChanges } from "./state/changes";
import { decode, DEMO_START, encode, fromPreset, isEdited, presetOf, type ViewState } from "./state/url";
import { TopBar } from "./components/TopBar";
import { Controls } from "./components/Controls";
import { buildGeometry, CountyMap, type MapGeometry } from "./components/CountyMap";
import { Shortlist } from "./components/Shortlist";
import { FindingPanel } from "./components/FindingPanel";

const TOP_N = 10;

export default function App() {
  const [state, setState] = useState<{ data: CockpitData; topo: Topology } | { error: string } | null>(null);
  useEffect(() => {
    Promise.all([loadCockpit(), loadGeometry()])
      .then(([data, topo]) => setState({ data, topo }))
      .catch((e: unknown) => setState({ error: e instanceof Error ? e.message : String(e) }));
  }, []);
  if (!state) return <div className="boot">Loading county data…</div>;
  if ("error" in state)
    return (
      <div className="boot boot-error" role="alert">
        <p>The cockpit couldn't load its data.</p>
        <p className="fine">{state.error}</p>
      </div>
    );
  return <Cockpit data={state.data} topo={state.topo} />;
}

function useDrawerMode() {
  const q = "(max-width: 1599px), (max-height: 899px)";
  const [m, setM] = useState(() => window.matchMedia(q).matches);
  useEffect(() => {
    const mq = window.matchMedia(q);
    const on = () => setM(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return m;
}

function Cockpit({ data, topo }: { data: CockpitData; topo: Topology }) {
  const initial = useMemo(() => decode(data, window.location.search), [data]);
  const [view, setView] = useState<ViewState>(initial.view);
  const [notice, setNotice] = useState<string | null>(
    initial.ignored.length ? `Ignored from the link: ${initial.ignored.join(", ")}.` : null,
  );
  const geo: MapGeometry = useMemo(() => buildGeometry(topo, data), [topo, data]);
  const drawer = useDrawerMode();
  const [drawerOpen, setDrawerOpen] = useState(true);

  const idxOf = useMemo(() => new Map(data.counties.fips.map((f, i) => [f, i])), [data]);
  const selected = view.selected ? (idxOf.get(view.selected) ?? null) : null;
  const compare = view.compare ? (idxOf.get(view.compare) ?? null) : null;
  const preset = presetOf(data, view.conditions.presetId);

  // URL follows state, so any moment can be reopened from its link.
  useEffect(() => {
    window.history.replaceState(null, "", encode(data, view));
  }, [data, view]);

  const result: RunResult = useMemo(
    () => run(data, view.conditions, { topN: TOP_N, robustness: preset.robustness, withStability: false }),
    [data, view.conditions, preset],
  );

  // Rank stability is heavier; it follows the result after input settles.
  const [stab, setStab] = useState<{ for: RunResult; s: Stability } | null>(null);
  useEffect(() => {
    const t = window.setTimeout(() => setStab({ for: result, s: stabilityFor(result, preset.robustness) }), 140);
    return () => window.clearTimeout(t);
  }, [result, preset]);

  // Rank movement since the previous result.
  const prev = useRef<RunResult | null>(null);
  const [changes, setChanges] = useState<RankChanges>(NO_CHANGES);
  useEffect(() => {
    if (prev.current && prev.current !== result) setChanges(computeChanges(data, prev.current, result, TOP_N));
    prev.current = result;
  }, [data, result]);

  const setConditions = useCallback((f: (c: Conditions) => Conditions) => {
    setView((v) => ({ ...v, conditions: f(v.conditions) }));
  }, []);

  const onPreset = (id: string) => setConditions(() => fromPreset(presetOf(data, id)));
  const onWeight = (p: string, w: number) => setConditions((c) => ({ ...c, weights: { ...c.weights, [p]: w } }));
  const onGate = (k: string, v: GateValue) => setConditions((c) => ({ ...c, gates: { ...c.gates, [k]: v } }));
  const onSelect = (i: number | null) => {
    setView((v) => ({ ...v, selected: i === null ? null : data.counties.fips[i]!, compare: i === null ? null : v.compare }));
    if (i !== null) setDrawerOpen(true);
  };
  const onCompare = (i: number | null) => setView((v) => ({ ...v, compare: i === null ? null : data.counties.fips[i]! }));

  const onReset = () => {
    const start = decode(data, `?preset=${DEMO_START.preset}`).view;
    prev.current = null;
    setChanges(NO_CHANGES);
    setNotice(null);
    setDrawerOpen(true);
    setView(start);
  };

  const stability = stab?.s ?? null;
  const stale = stab !== null && stab.for !== result;

  return (
    <div className={`app${drawer ? " is-compact" : ""}`}>
      <TopBar
        data={data}
        conditions={view.conditions}
        edited={isEdited(data, view.conditions)}
        onPreset={onPreset}
        onHorizon={(h) => setConditions((c) => ({ ...c, horizon: h }))}
        onScenario={(s) => setConditions((c) => ({ ...c, scenario: s }))}
        onCooling={(cool) => setConditions((c) => ({ ...c, facility: { ...c.facility, cooling: cool } }))}
        onReset={onReset}
      />
      {notice && (
        <div className="notice" role="status">
          {notice}
          <button className="link" onClick={() => setNotice(null)}>
            Dismiss
          </button>
        </div>
      )}
      <Controls data={data} conditions={view.conditions} result={result} onWeight={onWeight} onGate={onGate} />
      <main className="center">
        <CountyMap
          data={data}
          geo={geo}
          result={result}
          selected={selected}
          compare={compare}
          onSelect={onSelect}
          coveredBelow={drawer && selected !== null ? (drawerOpen ? 0.5 : 0.08) : 0}
        />
        <FindingPanel
          data={data}
          result={result}
          stability={stability}
          stabilityStale={stale}
          idx={selected}
          compare={compare}
          onCompare={onCompare}
          onClose={() => onSelect(null)}
          drawer={drawer}
          open={drawerOpen}
          onToggle={() => setDrawerOpen((o) => !o)}
        />
      </main>
      <aside className="right" aria-label="Shortlist">
        <Shortlist
          data={data}
          result={result}
          stability={stability}
          stabilityStale={stale}
          changes={changes}
          selected={selected}
          compare={compare}
          onSelect={(i) => onSelect(i)}
        />
      </aside>
    </div>
  );
}
