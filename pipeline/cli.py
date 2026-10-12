"""CLI: python -m pipeline.cli data/sample/gram_panchayat_sample.csv

Prints the grounded Marathi report and the verification summary.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .run import run_pipeline


def render_text(slots: list[dict]) -> str:
    lines = []
    for slot in slots:
        lines.append("".join(t["text"] for t in slot["tokens"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Marathi grounded report generator")
    ap.add_argument("csv", help="path to a source CSV")
    ap.add_argument("--engine", default="auto", choices=["auto", "llm", "deterministic"])
    ap.add_argument("--schema", default=None)
    ap.add_argument("--lexicon", default=None)
    ap.add_argument("--row", type=int, default=1, help="data row (1-indexed)")
    args = ap.parse_args(argv)

    csv_text = Path(args.csv).read_text(encoding="utf-8")
    result = run_pipeline(csv_text, schema=args.schema, lexicon=args.lexicon,
                          engine=args.engine, row_index=args.row)

    v = result["verification"]
    print(f"\n--- अहवाल / report (engine: {result['engine']}) ---")
    print(render_text(result["slots"]))
    print("\n--- verification ---")
    status = "OK" if v["ok"] else "FAIL"
    print(f"[{status}] {v['traceable']}/{v['total']} claims traceable, "
          f"{v['unsupported']} unsupported")
    for c in v["claims"]:
        mark = "ok" if c["valid"] else "BAD"
        print(f"  [{mark}] {c['field']:<16} = {c['value']:<18} <- {c['cell']}")
    for u in v["unsupported_detail"]:
        print(f"  [!!] {u['reason']}: {u.get('text','')}")
    return 0 if v["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
