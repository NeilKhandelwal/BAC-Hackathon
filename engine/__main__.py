"""CLI: python -m engine rank --conditions ... --features ... --out results/<preset>.csv"""
import argparse
import json
import sys
from pathlib import Path

from engine.explain import explain, format_text
from engine.rank import load_features, load_yaml, rank, unit

PILLARS = Path(__file__).with_name("pillars.yaml")


def cmd_rank(args):
    conditions = load_yaml(args.conditions)
    u = unit(conditions)
    df, warnings = load_features(args.features, u["key"])
    ranked, excluded, report = rank(df, conditions, load_yaml(args.pillars))
    report["warnings"] = warnings + report["warnings"]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(out, index=False, float_format="%.2f")
    excluded.to_csv(out.with_name(out.stem + "_excluded.csv"), index=False)
    out.with_name(out.stem + "_report.json").write_text(json.dumps(report, indent=2))

    for w in report["warnings"]:
        print(f"warning: {w}", file=sys.stderr)
    print(f"{conditions.get('name')}: {report['passed']} of {report['counties']} counties pass the gates, "
          f"{report['floor_ok']} pass the floor rule")
    for gate, n in sorted(report["gate_failures"].items(), key=lambda kv: -kv[1]):
        print(f"  failed {gate}: {n}")
    top_n = (conditions.get("output") or {}).get("top_n", 10)
    cols = ["rank", u["key"], u["name"], u["group"], "composite", "robustness", "rank_delta_2050", "floor_ok"] + \
        [c for c in ranked.columns if c.startswith("pillar_")]
    print(ranked[[c for c in cols if c in ranked.columns]].head(top_n).to_string(index=False, float_format="%.1f"))


def cmd_explain(args):
    conditions = load_yaml(args.conditions)
    u = unit(conditions)
    df, _ = load_features(args.features, u["key"])
    try:
        e = explain(df, conditions, load_yaml(args.pillars), args.fips)
    except KeyError as err:  # unknown fips; other KeyErrors are bugs and keep their traceback
        raise ValueError(err.args[0]) from err
    print(json.dumps(e, indent=2) if args.json else format_text(e, u))


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m engine")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rank", help="rank counties for one conditions file")
    r.add_argument("--conditions", required=True)
    r.add_argument("--features", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--pillars", default=str(PILLARS))
    r.set_defaults(func=cmd_rank)
    e = sub.add_parser("explain", help="per-county breakdown")
    e.add_argument("--conditions", required=True)
    e.add_argument("--fips", "--id", dest="fips", required=True, help="row key, such as a fips or an iso3")
    e.add_argument("--features", default="data/processed/county_features.parquet")
    e.add_argument("--pillars", default=str(PILLARS))
    e.add_argument("--json", action="store_true")
    e.set_defaults(func=cmd_explain)
    args = p.parse_args(argv)
    try:
        args.func(args)
    except ValueError as err:  # bad conditions or input, such as horizon 2040; exit 2 like argparse
        print(f"error: {err}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
