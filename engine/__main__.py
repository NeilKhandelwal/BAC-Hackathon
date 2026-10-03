"""CLI: python -m engine rank --conditions ... --features ... --out results/<preset>.csv"""
import argparse
import json
import sys
from pathlib import Path

from engine.rank import load_features, load_yaml, rank

PILLARS = Path(__file__).with_name("pillars.yaml")


def cmd_rank(args):
    conditions = load_yaml(args.conditions)
    df, warnings = load_features(args.features)
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
    cols = ["rank", "fips", "county_name", "state", "composite", "floor_ok"] + \
        [c for c in ranked.columns if c.startswith("pillar_")]
    print(ranked[[c for c in cols if c in ranked.columns]].head(top_n).to_string(index=False, float_format="%.1f"))


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m engine")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rank", help="rank counties for one conditions file")
    r.add_argument("--conditions", required=True)
    r.add_argument("--features", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--pillars", default=str(PILLARS))
    r.set_defaults(func=cmd_rank)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
