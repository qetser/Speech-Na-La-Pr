"""Fetch real Marathi (Wikipedia, wikimedia/wikipedia 20231101.mr) and build a
leakage-free train / held-out split BY ARTICLE.

    python -m scripts.fetch_marathi_wiki

Writes (data/corpus/real/, gitignored except the held-out file):
  train_wiki.txt     ~all training articles, one paragraph per line
  heldout_wiki.txt   paragraphs from held-out articles (never seen in training)
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

from datasets import load_dataset

OUT = Path(__file__).resolve().parent.parent / "data" / "corpus" / "real"
HELDOUT_ARTICLE_PCT = 2          # % of articles reserved for evaluation
HELDOUT_MAX_WORDS = 60_000
_DEVA = re.compile(r"[ऀ-ॿ]")


def _is_heldout(title: str) -> bool:
    return int(hashlib.md5(title.encode()).hexdigest(), 16) % 100 < HELDOUT_ARTICLE_PCT


def _paragraphs(text: str):
    for line in text.split("\n"):
        line = unicodedata.normalize("NFC", line.strip())
        if len(line.split()) < 8:
            continue
        # keep mostly-Devanagari lines (drop English/ref/table residue)
        if len(_DEVA.findall(line)) / max(len(line), 1) < 0.6:
            continue
        yield line


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ds = load_dataset("wikimedia/wikipedia", "20231101.mr", split="train")
    n_tr = n_te = 0
    with open(OUT / "train_wiki.txt", "w", encoding="utf-8") as tr, \
         open(OUT / "heldout_wiki.txt", "w", encoding="utf-8") as te:
        for row in ds:
            paras = list(_paragraphs(row["text"]))
            if not paras:
                continue
            if _is_heldout(row["title"]):
                if n_te < HELDOUT_MAX_WORDS:
                    # at most 3 paragraphs/article -> more topical diversity
                    for p in paras[:3]:
                        te.write(p + "\n"); n_te += len(p.split())
            else:
                for p in paras:
                    tr.write(p + "\n"); n_tr += len(p.split())
    print(f"train words: {n_tr:,}   held-out words: {n_te:,}")


if __name__ == "__main__":
    main()
