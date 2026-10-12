"""Evaluation metrics beyond BLEU (plan.md Component 6).

- faithfulness_rate : fraction of numeric/entity claims traceable to a source cell
                      (our core guarantee; comes straight from the verifier)
- chrf              : chrF++ character-n-gram F-score vs a gold report
                      (correlates better than BLEU for inflectional low-resource
                      languages: 2602.17425)
- codemix_rate      : fraction of word tokens written in Latin script (register drift)
- token_cost        : word count (cheap proxy for generation cost)
"""
from __future__ import annotations

import re

_WORD = re.compile(r"\S+")
_LATIN = re.compile(r"[A-Za-z]")


def faithfulness_rate(verification: dict) -> float:
    total = verification.get("total", 0)
    if total == 0:
        return 1.0
    return verification.get("traceable", 0) / total


def codemix_rate(text: str) -> float:
    words = _WORD.findall(text)
    if not words:
        return 0.0
    latin = sum(1 for w in words if _LATIN.search(w))
    return latin / len(words)


def token_cost(text: str) -> int:
    return len(_WORD.findall(text))


def chrf(hyp: str, ref: str, max_n: int = 6, beta: int = 2) -> float:
    """chrF (character n-gram F-beta). Uses sacrebleu if available, else a
    self-contained implementation so eval runs with zero extra deps."""
    try:
        import sacrebleu
        return sacrebleu.sentence_chrf(hyp, [ref]).score / 100.0
    except Exception:
        pass

    def ngrams(s: str, n: int):
        s = re.sub(r"\s+", "", s)
        return [s[i:i + n] for i in range(len(s) - n + 1)]

    f_scores = []
    for n in range(1, max_n + 1):
        h, r = ngrams(hyp, n), ngrams(ref, n)
        if not h or not r:
            continue
        from collections import Counter
        hc, rc = Counter(h), Counter(r)
        overlap = sum((hc & rc).values())
        prec = overlap / len(h)
        rec = overlap / len(r)
        if prec + rec == 0:
            f_scores.append(0.0)
        else:
            b2 = beta * beta
            f_scores.append((1 + b2) * prec * rec / (b2 * prec + rec))
    return sum(f_scores) / len(f_scores) if f_scores else 0.0
