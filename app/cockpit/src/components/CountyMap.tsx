import { memo, useEffect, useMemo, useRef, useState } from "react";
import { geoConicEqualArea, geoPath } from "d3-geo";
import { quantile } from "d3-array";
import { feature, mesh } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { CockpitData } from "../data/types";
import type { RunResult } from "../engine/run";
import { fmtInt, fmtScore } from "../lib/format";

const W = 1000;
const H = 620;
const RAMP = 7;
const MIN_K = 1;
const MAX_K = 12;
const BUTTON_STEP = 1.6;

interface View {
  k: number;
  tx: number;
  ty: number;
}

/** Zoom by `f` around point (px, py) in map units, keeping that point still. */
function zoomAt(v: View, f: number, px: number, py: number): View {
  const k = Math.min(MAX_K, Math.max(MIN_K, v.k * f));
  const r = k / v.k;
  return clampView({ k, tx: px - (px - v.tx) * r, ty: py - (py - v.ty) * r });
}

/** Keep the map in the frame: at least three quarters of the frame stays on the map. */
function clampView(v: View): View {
  if (v.k <= 1) return { k: 1, tx: 0, ty: 0 };
  const mx = W * 0.25;
  const my = H * 0.25;
  return {
    k: v.k,
    tx: Math.min(mx, Math.max(W - W * v.k - mx, v.tx)),
    ty: Math.min(my, Math.max(H - H * v.k - my, v.ty)),
  };
}

type Props = { fips: string; county_name: string; state: string };

export interface MapGeometry {
  paths: string[]; // aligned with data.counties index
  bounds: [[number, number], [number, number]][];
  centroid: [number, number][];
  borders: string; // county borders within a state, drawn once over the fills
  states: string;
  nation: string;
}

export function buildGeometry(topo: Topology, data: CockpitData): MapGeometry {
  const obj = topo.objects.counties as GeometryCollection<Props>;
  const fc = feature(topo, obj) as FeatureCollection<Geometry, Props>;
  const projection = geoConicEqualArea().parallels([29.5, 45.5]).rotate([96, 0]).fitExtent(
    [
      [8, 8],
      [W - 8, H - 8],
    ],
    fc,
  );
  const path = geoPath(projection);
  const byFips = new Map<string, Feature<Geometry, Props>>();
  for (const f of fc.features) byFips.set(f.properties.fips, f);
  const paths: string[] = [];
  const bounds: MapGeometry["bounds"] = [];
  const centroid: [number, number][] = [];
  for (let i = 0; i < data.counties.fips.length; i++) {
    const f = byFips.get(data.counties.fips[i]!);
    if (!f) {
      paths.push("");
      bounds.push([
        [0, 0],
        [0, 0],
      ]);
      const p = projection([data.counties.lon[i]!, data.counties.lat[i]!]) ?? [0, 0];
      centroid.push([p[0], p[1]]);
      continue;
    }
    paths.push(path(f) ?? "");
    bounds.push(path.bounds(f));
    const c = path.centroid(f);
    centroid.push([c[0], c[1]]);
  }
  const sameState = (a: { properties?: unknown }, b: { properties?: unknown }) =>
    (a.properties as Props).state === (b.properties as Props).state;
  const borders = path(mesh(topo, obj, (a, b) => a !== b && sameState(a, b))) ?? "";
  const states = path(mesh(topo, obj, (a, b) => a !== b && !sameState(a, b))) ?? "";
  const nation = path(mesh(topo, obj, (a, b) => a === b)) ?? "";
  return { paths, bounds, centroid, borders, states, nation };
}

interface MapProps {
  data: CockpitData;
  geo: MapGeometry;
  result: RunResult;
  selected: number | null;
  compare: number | null;
  onSelect: (idx: number | null) => void;
  /** share of the map height covered from below, so a selection centers in the visible part */
  coveredBelow?: number;
  /** changes when the app resets, so a hand-set zoom resets with it */
  resetKey?: number;
}

export function CountyMap({ data, geo, result, selected, compare, onSelect, coveredBelow = 0, resetKey = 0 }: MapProps) {
  const [hover, setHover] = useState<number | null>(null);

  // Quantile breaks of the composite among gate-passing counties.
  const breaks = useMemo(() => {
    const vals = result.ranked.map((i) => result.comp[i]!).filter((x) => !Number.isNaN(x)).sort((a, b) => a - b);
    return Array.from({ length: RAMP - 1 }, (_, k) => quantile(vals, (k + 1) / RAMP) ?? 0);
  }, [result]);

  const fills = useMemo(() => {
    const n = data.counties.fips.length;
    const f: string[] = new Array(n);
    for (let i = 0; i < n; i++) {
      if (!result.gates.passed[i]) f[i] = "x";
      else {
        const v = result.comp[i]!;
        if (Number.isNaN(v)) f[i] = "n";
        else {
          let k = 0;
          while (k < breaks.length && v > breaks[k]!) k++;
          f[i] = `${k + 1}${result.floor[i] ? "" : "f"}`;
        }
      }
    }
    return f;
  }, [result, breaks, data]);

  const selectionView = useMemo<View>(() => {
    if (selected === null) return { k: 1, tx: 0, ty: 0 };
    const [[x0, y0], [x1, y1]] = geo.bounds[selected]!;
    const cx = (x0 + x1) / 2;
    const cy = (y0 + y1) / 2;
    const extent = Math.max(Math.max(x1 - x0, y1 - y0) * 3, 120);
    const k = Math.min(8, Math.max(1, Math.min(W, H) / extent));
    const visibleMid = (H * (1 - coveredBelow)) / 2;
    return { k, tx: W / 2 - k * cx, ty: visibleMid - k * cy };
  }, [selected, geo, coveredBelow]);

  // A hand-set view (wheel, pinch, drag, buttons) wins until the selection changes or the app resets.
  const [userView, setUserView] = useState<View | null>(null);
  useEffect(() => setUserView(null), [selected, resetKey]);
  const view = userView ?? selectionView;
  const viewRef = useRef(view);
  viewRef.current = view;

  // While the user drives the view, follow the input directly instead of easing toward it.
  const [interacting, setInteracting] = useState(false);
  const idle = useRef<number | undefined>(undefined);
  const touch = () => {
    setInteracting(true);
    window.clearTimeout(idle.current);
    idle.current = window.setTimeout(() => setInteracting(false), 160);
  };

  const svgRef = useRef<SVGSVGElement>(null);
  /** client pixels to map units, through the svg's viewBox scaling */
  const toMap = (clientX: number, clientY: number): [number, number] => {
    const svg = svgRef.current!;
    const pt = svg.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    const m = svg.getScreenCTM();
    if (!m) return [W / 2, H / 2];
    const p = pt.matrixTransform(m.inverse());
    return [p.x, p.y];
  };

  // Wheel and trackpad: scroll or pinch to zoom around the pointer. React's
  // wheel handler is passive, so this listener is attached by hand to stop
  // the page from scrolling.
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const dy = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
      // a pinch arrives as ctrl+wheel with small deltas
      const f = Math.exp(-dy * (e.ctrlKey ? 0.01 : 0.0015));
      const [px, py] = toMap(e.clientX, e.clientY);
      touch();
      setUserView(zoomAt(viewRef.current, f, px, py));
    };
    svg.addEventListener("wheel", onWheel, { passive: false });
    return () => svg.removeEventListener("wheel", onWheel);
  }, []);

  // Drag to pan once zoomed in. A press that doesn't move stays a click.
  const drag = useRef<{ x: number; y: number; v: View; moved: boolean; id: number } | null>(null);
  const onPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    if (e.button !== 0 || viewRef.current.k <= 1) return;
    drag.current = { x: e.clientX, y: e.clientY, v: viewRef.current, moved: false, id: e.pointerId };
  };
  const onPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const d = drag.current;
    if (!d || d.id !== e.pointerId) return;
    const [ax, ay] = toMap(d.x, d.y);
    const [bx, by] = toMap(e.clientX, e.clientY);
    if (!d.moved && Math.hypot(e.clientX - d.x, e.clientY - d.y) < 4) return;
    if (!d.moved) {
      d.moved = true;
      svgRef.current?.setPointerCapture(e.pointerId);
    }
    touch();
    setUserView(clampView({ k: d.v.k, tx: d.v.tx + (bx - ax), ty: d.v.ty + (by - ay) }));
  };
  const endDrag = (e: React.PointerEvent<SVGSVGElement>) => {
    const d = drag.current;
    if (!d || d.id !== e.pointerId) return;
    if (d.moved) {
      // swallow the click that follows a drag
      const stop = (ev: MouseEvent) => ev.stopPropagation();
      window.addEventListener("click", stop, { capture: true, once: true });
      window.setTimeout(() => window.removeEventListener("click", stop, { capture: true }), 0);
    }
    drag.current = null;
  };

  const visibleMid = (H * (1 - coveredBelow)) / 2;
  const zoomBy = (f: number) => setUserView(zoomAt(view, f, W / 2, visibleMid));

  const top = result.ranked.slice(0, result.topN);
  const zoomed = view.k > 1;
  const hovered = hover ?? null;

  return (
    <div className={`map-frame${interacting ? " is-interacting" : ""}${zoomed ? " is-zoomed" : ""}`}>
      <svg
        ref={svgRef}
        className="map"
        viewBox={`0 0 ${W} ${H}`}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        role="img"
        aria-label={`Map of ${fmtInt(data.counties.fips.length)} counties. ${fmtInt(result.passedCount)} pass the gates. Use the shortlist or Find a county to select one.`}
        onClick={(e) => {
          const t = e.target as SVGElement;
          const i = t.getAttribute("data-i");
          if (i !== null) onSelect(Number(i));
        }}
        onMouseOver={(e) => {
          const i = (e.target as SVGElement).getAttribute("data-i");
          setHover(i === null ? null : Number(i));
        }}
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform={`rotate(45) scale(${1 / view.k})`}>
            <rect width="5" height="5" fill="var(--ground)" />
            <line x1="0" y1="0" x2="0" y2="5" stroke="var(--hatch)" strokeWidth="1" />
          </pattern>
        </defs>
        <g
          className="zoom"
          style={{ transform: `translate(${view.tx}px, ${view.ty}px) scale(${view.k})` }}
        >
          <Counties paths={geo.paths} fills={fills} />
          <path d={geo.borders} className="borders" />
          <path d={geo.states} className="states" />
          <path d={geo.nation} className="nation" />
          {compare !== null && <path d={geo.paths[compare]} className="outline-compare" />}
          {selected !== null && (
            <>
              <path d={geo.paths[selected]} className="outline-halo" />
              <path d={geo.paths[selected]} className="outline-selected" />
            </>
          )}
          {hovered !== null && hovered !== selected && <path d={geo.paths[hovered]} className="outline-hover" />}
        </g>
        <g className="rings" aria-hidden>
          {top.map((idx, r) => {
            const [x, y] = geo.centroid[idx]!;
            return (
              <g key={r} className="ring" style={{ transform: `translate(${x * view.k + view.tx}px, ${y * view.k + view.ty}px)` }}>
                <circle r={13} />
                <text dy="0.35em">{r + 1}</text>
              </g>
            );
          })}
        </g>
      </svg>

      <div className="map-toolbar">
        <CountySearch data={data} onSelect={onSelect} />
        {zoomed && (
          <button
            className="btn btn-quiet"
            onClick={() => {
              setUserView(null);
              onSelect(null);
            }}
          >
            Show all counties
          </button>
        )}
        <span className="map-hover" aria-hidden>
          {hovered !== null &&
            `${data.counties.name[hovered]}, ${data.counties.state[hovered]} · ${
              result.gates.passed[hovered] ? `rank ${fmtInt(result.rankOf[hovered]!)}` : "excluded"
            }`}
        </span>
      </div>

      {zoomed && (
        <svg className="inset" viewBox={`0 0 ${W} ${H}`} aria-hidden>
          <path d={geo.nation} className="inset-nation" />
          <path d={geo.states} className="inset-states" />
          <rect x={-view.tx / view.k} y={-view.ty / view.k} width={W / view.k} height={H / view.k} className="inset-view" />
        </svg>
      )}

      <div className="zoom-controls" role="group" aria-label="Map zoom" style={{ bottom: `calc(${coveredBelow * 100}% + 12px)` }}>
        <button type="button" className="zoom-btn" aria-label="Zoom in" disabled={view.k >= MAX_K - 1e-6} onClick={() => zoomBy(BUTTON_STEP)}>
          <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden>
            <path d="M8 3v10M3 8h10" />
          </svg>
        </button>
        <button type="button" className="zoom-btn" aria-label="Zoom out" disabled={view.k <= MIN_K + 1e-6} onClick={() => zoomBy(1 / BUTTON_STEP)}>
          <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden>
            <path d="M3 8h10" />
          </svg>
        </button>
      </div>

      <Legend breaks={breaks} />
    </div>
  );
}

const Counties = memo(function Counties({ paths, fills }: { paths: string[]; fills: string[] }) {
  return (
    <g className="counties">
      {paths.map((d, i) =>
        d ? <path key={i} d={d} data-i={i} className={`c c${fills[i]}`} /> : null,
      )}
    </g>
  );
});

function Legend({ breaks }: { breaks: number[] }) {
  return (
    <div className="legend" aria-label="Map legend">
      <div className="legend-ramp">
        <span className="legend-title">Composite score, gate-passing counties</span>
        <div className="ramp">
          {Array.from({ length: RAMP }, (_, k) => (
            <span key={k} className={`ramp-cell c${k + 1}`} />
          ))}
        </div>
        <div className="ramp-labels">
          <span>{fmtScore(breaks[0] ?? NaN)}</span>
          <span>{fmtScore(breaks[Math.floor(breaks.length / 2)] ?? NaN)}</span>
          <span>{fmtScore(breaks[breaks.length - 1] ?? NaN)}</span>
        </div>
      </div>
      <div className="legend-keys">
        <span className="key">
          <svg width="18" height="14" aria-hidden>
            <rect width="18" height="14" fill="url(#hatch)" stroke="var(--rule-strong)" />
          </svg>
          Excluded by a gate
        </span>
        <span className="key">
          <span className="key-sw c5f" />
          Below a pillar floor
        </span>
        <span className="key">
          <svg width="20" height="20" aria-hidden className="key-ring">
            <circle cx="10" cy="10" r="8.5" />
            <text x="10" y="10" dy="0.35em">
              1
            </text>
          </svg>
          Top 10 rank
        </span>
      </div>
    </div>
  );
}

function CountySearch({ data, onSelect }: { data: CockpitData; onSelect: (i: number | null) => void }) {
  const options = useMemo(
    () => data.counties.fips.map((f, i) => ({ label: `${data.counties.name[i]}, ${data.counties.state[i]} (${f})`, i })),
    [data],
  );
  const lookup = useMemo(() => new Map(options.map((o) => [o.label.toLowerCase(), o.i])), [options]);
  const [q, setQ] = useState("");
  const [miss, setMiss] = useState(false);
  const submit = (value: string) => {
    const v = value.trim().toLowerCase();
    let i = lookup.get(v);
    if (i === undefined && /^\d{5}$/.test(v)) i = data.counties.fips.indexOf(v);
    if (i === undefined || i < 0) {
      const hit = options.find((o) => o.label.toLowerCase().startsWith(v));
      i = hit?.i;
    }
    if (i !== undefined && i >= 0 && v) {
      onSelect(i);
      setQ("");
      setMiss(false);
    } else setMiss(v.length > 0);
  };
  return (
    <form
      className="search"
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        submit(q);
      }}
    >
      <label htmlFor="county-search" className="visually-hidden">
        Find a county
      </label>
      <input
        id="county-search"
        list="county-options"
        placeholder="Find a county or FIPS"
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setMiss(false);
          if (lookup.has(e.target.value.toLowerCase())) submit(e.target.value);
        }}
        aria-invalid={miss}
        aria-describedby={miss ? "search-miss" : undefined}
      />
      <datalist id="county-options">
        {options.map((o) => (
          <option key={o.i} value={o.label} />
        ))}
      </datalist>
      {miss && (
        <span id="search-miss" className="search-miss">
          No county matches
        </span>
      )}
    </form>
  );
}
