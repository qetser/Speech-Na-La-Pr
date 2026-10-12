"""Evaluation harness: run every available system over the benchmark and print
the B0-B4 results table (plan.md Component 6).

Benchmark layout:
    data/benchmark/<id>/input.csv     source table
    data/benchmark/<id>/gold.txt      gold Marathi report (optional, enables chrF)

Usage:
    python -m eval.run_eval                       # default benchmark dir
    python -m eval.run_eval --benchmark data/benchmark
"""
from __future__ import annotations

import argparse
from pathlib import Path
from statistics import mean

from eval.baselines import available_systems
from eval.metrics import chrf, codemix_rate, faithfulness_rate, token_cost

ROOT = Path(__file__).resolve().parent.parent


def load_benchmark(bench_dir: Path) -> list[dict]:
    items = []
    for d in sorted(p for p in bench_dir.iterdir() if p.is_dir()):
        csv_path = d / "input.csv"
        if not csv_path.exists():
            continue
        gold = (d / "gold.txt")
        items.append({
            "id": d.name,
            "csv": csv_path.read_text(encoding="utf-8"),
            "gold": gold.read_text(encoding="utf-8").strip() if gold.exists() else None,
        })
    return items


def evaluate(bench_dir: Path) -> dict[str, dict]:
    items = load_benchmark(bench_dir)
    if not items:
        raise SystemExit(f"No benchmark items in {bench_dir}")
    systems = available_systems()
    table: dict[str, dict] = {}
    for name, run in systems.items():
        faith, cmix, cost, chrfs = [], [], [], []
        for it in items:
            text, verification = run(it["csv"])
            faith.append(faithfulness_rate(verification))
            cmix.append(codemix_rate(text))
            cost.append(token_cost(text))
            if it["gold"]:
                chrfs.append(chrf(text, it["gold"]))
        table[name] = {
            "faithfulness": round(mean(faith), 3),
            "codemix_rate": round(mean(cmix), 3),
            "token_cost": round(mean(cost), 1),
            "chrf": round(mean(chrfs), 3) if chrfs else None,
            "n": len(items),
        }
    return table


def print_table(table: dict[str, dict]) -> None:
    cols = ["faithfulness", "chrf", "codemix_rate", "token_cost", "n"]
    print(f"\n{'system':<30}" + "".join(f"{c:>15}" for c in cols))
    print("-" * (30 + 15 * len(cols)))
    for name, row in table.items():
        cells = "".join(f"{('-' if row[c] is None else row[c])!s:>15}" for c in cols)
        print(f"{name:<30}{cells}")
    print("\nfaithfulness = fraction of numeric claims traceable to source "
          "(1.000 = zero hallucinated figures)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", default=str(ROOT / "data" / "benchmark"))
    args = ap.parse_args(argv)
    print_table(evaluate(Path(args.benchmark)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
