"""Actual testing at scale + audit data for the figure.

1. Retrain the Marathi tokenizer on the large corpus; measure fertility.
2. Over ALL 500 reports (deterministic, offline): verify faithfulness and measure
   tokens-per-report for our tokenizer vs GPT-4o's.
3. Over a sample: run B1 (ungrounded LLM) vs B4 (grounded LLM) faithfulness.
Writes eval/audit.json for the figure.
"""
import json
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import train_tokenizer as TT
from pipeline.generate import generate_deterministic, llm_available
from pipeline.ground import ground
from pipeline.parse import parse_csv
from pipeline.report import _report_text, build_comparison
from pipeline.run import DEFAULT_SCHEMA
from pipeline.schema import load_schema
from pipeline.verify import verify

random.seed(7)
schema = load_schema(DEFAULT_SCHEMA)
CORPUS = ROOT / "data" / "corpus" / "marathi_admin_large.txt"
REPORTS = ROOT / "data" / "benchmark_large" / "reports.csv"
HEADER = "gp_name,taluka,district,period,households,works_done,funds_received,funds_spent,beneficiaries"

# --- 1. retrain tokenizer on the big corpus ---
print("retraining tokenizer on large corpus...")
TT.train(corpus=CORPUS, vocab_size=4000)
fertility = {k: v for k, v in TT.evaluate().items()}
print("fertility:", fertility)

import tiktoken
from tokenizers import Tokenizer
ours = Tokenizer.from_file(str(TT.OUT))
gpt = tiktoken.get_encoding("o200k_base")

# --- 2. deterministic audit over all 500 ---
rows = REPORTS.read_text(encoding="utf-8").splitlines()[1:]
det_faith, our_tok, gpt_tok, n_figs = [], [], [], []
for line in rows:
    csv_text = HEADER + "\n" + line
    record = parse_csv(csv_text)
    slots = generate_deterministic(ground(record, schema), schema)
    v = verify(slots, record)
    det_faith.append(v["traceable"] / max(v["total"], 1))
    text = _report_text("", [{"heading": "", "tokens": s["tokens"]} for s in slots])
    our_tok.append(len(ours.encode(text).tokens))
    gpt_tok.append(len(gpt.encode(text)))
    n_figs.append(v["total"])
print(f"deterministic faithfulness over {len(rows)}: min={min(det_faith)} mean={sum(det_faith)/len(det_faith):.3f}")

# --- 3. LLM B1 vs B4 on a sample ---
sample_idx = sorted(random.sample(range(len(rows)), 20)) if llm_available() else []
b1, b4 = [], []
for k, i in enumerate(sample_idx):
    rec = parse_csv(HEADER + "\n" + rows[i])
    facts = [{"label": kk, "value": c.value} for kk, c in rec.items()]
    try:
        out = build_comparison("ग्रामपंचायत कार्य अहवाल", facts, "Activity report", "", engine="llm")
        b4.append(out["grounded"]["verification"]["traceable"] / max(out["grounded"]["verification"]["total"], 1))
        if out["ungrounded"]:
            uv = out["ungrounded"]["verification"]
            b1.append(uv["traceable"] / max(uv["total"], 1))
        print(f"  [{k+1}/{len(sample_idx)}] B1={b1[-1]:.2f} B4={b4[-1]:.2f}")
    except Exception as e:
        print("  sample failed:", e)

audit = {
    "n_reports": len(rows),
    "fertility": fertility,
    "det_faithfulness": det_faith,
    "our_tokens": our_tok,
    "gpt_tokens": gpt_tok,
    "n_figures": n_figs,
    "sample_b1": b1,
    "sample_b4": b4,
    "n_sample": len(b1),
}
(ROOT / "eval" / "audit.json").write_text(json.dumps(audit), encoding="utf-8")
print("saved eval/audit.json")
print(f"token savings (sum): GPT={sum(gpt_tok)} ours={sum(our_tok)} -> {sum(gpt_tok)/sum(our_tok):.2f}x")
if b1:
    print(f"sample faithfulness: B1={sum(b1)/len(b1):.3f}  B4={sum(b4)/len(b4):.3f}  (n={len(b1)})")
