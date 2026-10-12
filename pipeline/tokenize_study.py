"""Component 2: tokenizer fertility study for Marathi (Devanagari).

Fertility = subword tokens per word. Lower is better (cheaper, usually better
quality). We compare tokenizers on a Marathi corpus so the choice is measured,
not assumed (plan.md: MorphTok 2504.10335, BHARATI 2607.23319, Tokenizer Tax
2607.24276).

HuggingFace tokenizers are used when `transformers` is installed; otherwise the
character baseline still runs so the module never hard-fails.

    python -m pipeline.tokenize_study data/sample/marathi_corpus.txt \
        --tokenizers google/muril-base-cased ai4bharat/indic-bert
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

_WORD = re.compile(r"\S+")


def word_count(text: str) -> int:
    return len(_WORD.findall(text))


def char_fertility(text: str) -> float:
    """Baseline: a character tokenizer. Upper bound on fertility."""
    words = word_count(text) or 1
    non_space = len(re.sub(r"\s+", "", text))
    return non_space / words


def hf_fertility(text: str, name: str) -> float | None:
    try:
        from transformers import AutoTokenizer
    except ImportError:
        return None
    tok = AutoTokenizer.from_pretrained(name)
    n_tokens = len(tok.encode(text, add_special_tokens=False))
    return n_tokens / (word_count(text) or 1)


def study(corpus: str, tokenizers: list[str]) -> dict[str, float | None]:
    results: dict[str, float | None] = {"char-baseline": round(char_fertility(corpus), 3)}
    for name in tokenizers:
        f = hf_fertility(corpus, name)
        results[name] = round(f, 3) if f is not None else None
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Marathi tokenizer fertility study")
    ap.add_argument("corpus", help="path to a UTF-8 Marathi text file")
    ap.add_argument("--tokenizers", nargs="*", default=[])
    args = ap.parse_args(argv)
    text = Path(args.corpus).read_text(encoding="utf-8")
    print(f"words: {word_count(text)}")
    print(f"{'tokenizer':<32} {'fertility (tok/word)':>20}")
    for name, fert in study(text, args.tokenizers).items():
        shown = fert if fert is not None else "n/a (install transformers)"
        print(f"{name:<32} {str(shown):>20}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
