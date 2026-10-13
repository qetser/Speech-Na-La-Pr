"""Finalize: recompute the per-report token audit over all 500 reports with the
existing (Wikipedia-trained) tokenizer, and merge with the existing LLM faithfulness
sample. Writes eval/audit.json. Does NOT retrain the tokenizer
(use `python -m pipeline.train_tokenizer`).

CAVEAT: the 500 reports are template-generated, so token counts here are an
in-template cost figure, not evidence of general Marathi efficiency."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import train_tokenizer as TT
from pipeline.generate import generate_deterministic
from pipeline.ground import ground
from pipeline.parse import parse_csv
from pipeline.report import _report_text
from pipeline.run import DEFAULT_SCHEMA
from pipeline.schema import load_schema
from pipeline.verify import verify

schema = load_schema(DEFAULT_SCHEMA)
REPORTS = ROOT / "data/benchmark_large/reports.csv"
HEADER = "gp_name,taluka,district,period,households,works_done,funds_received,funds_spent,beneficiaries"

fertility = TT.evaluate()
print("held-out fertility:", {k: {n: v[0] for n, v in e["fertility"].items()} for k, e in fertility.items()})

import tiktoken
from tokenizers import Tokenizer
ours = Tokenizer.from_file(str(TT.OUT))
gpt = tiktoken.get_encoding("o200k_base")

rows = REPORTS.read_text(encoding="utf-8").splitlines()[1:]
det_faith, our_tok, gpt_tok, n_figs = [], [], [], []
for line in rows:
    rec = parse_csv(HEADER + "\n" + line)
    slots = generate_deterministic(ground(rec, schema), schema)
    v = verify(slots, rec)
    det_faith.append(v["traceable"] / max(v["total"], 1))
    text = _report_text("", [{"heading": "", "tokens": s["tokens"]} for s in slots])
    our_tok.append(len(ours.encode(text).tokens))
    gpt_tok.append(len(gpt.encode(text)))
    n_figs.append(v["total"])

# reuse the LLM sample from the previous audit run
prev = json.loads((ROOT / "eval/audit.json").read_text(encoding="utf-8"))
audit = {
    "n_reports": len(rows),
    "fertility": fertility,
    "det_faithfulness": det_faith,
    "our_tokens": our_tok, "gpt_tokens": gpt_tok, "n_figures": n_figs,
    "sample_b1": prev["sample_b1"], "sample_b4": prev["sample_b4"],
    "n_sample": prev["n_sample"],
}
(ROOT / "eval/audit.json").write_text(json.dumps(audit), encoding="utf-8")
print(f"deterministic faithfulness over {len(rows)}: mean={sum(det_faith)/len(det_faith):.3f} min={min(det_faith)}")
print(f"in-domain token savings: GPT={sum(gpt_tok)} ours={sum(our_tok)} -> {sum(gpt_tok)/sum(our_tok):.2f}x")
print(f"LLM sample (reused): B1={sum(prev['sample_b1'])/len(prev['sample_b1']):.3f} B4={sum(prev['sample_b4'])/len(prev['sample_b4']):.3f} n={prev['n_sample']}")
print("saved eval/audit.json")
