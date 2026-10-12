"""Component 2 (training): train a Marathi-specialized BPE tokenizer and compare
its subword fertility against GPT's tokenizer.

Fertility = tokens per word (lower is better: cheaper + usually better quality).
A tokenizer trained on Marathi should segment Devanagari far more efficiently
than an English-centric tokenizer (the "tokenizer tax", plan.md 2607.24276).

    python -m pipeline.train_tokenizer                 # train + evaluate
    python -m pipeline.train_tokenizer --vocab 1500
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from tokenizers import Tokenizer, models, normalizers, pre_tokenizers, trainers

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpus" / "marathi_admin.txt"
HELDOUT = ROOT / "data" / "corpus" / "eval_heldout.txt"
OUT = ROOT / "tokenizers" / "marathi_bpe.json"

_WORD = re.compile(r"\S+")


def train(corpus: Path = CORPUS, vocab_size: int = 2000, out: Path = OUT) -> Path:
    tok = Tokenizer(models.BPE(unk_token="<unk>"))
    tok.normalizer = normalizers.NFC()                     # canonical Devanagari
    tok.pre_tokenizer = pre_tokenizers.Whitespace()
    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size, min_frequency=2,
        special_tokens=["<unk>", "<pad>", "<s>", "</s>"],
    )
    files = [str(c) for c in (corpus if isinstance(corpus, (list, tuple)) else [corpus])]
    tok.train(files, trainer)
    out.parent.mkdir(parents=True, exist_ok=True)
    tok.save(str(out))
    return out


def _word_count(text: str) -> int:
    return len(_WORD.findall(text))


def fertility_our(text: str, model_path: Path = OUT) -> float:
    tok = Tokenizer.from_file(str(model_path))
    n = len(tok.encode(text).tokens)
    return n / (_word_count(text) or 1)


def fertility_tiktoken(text: str, encoding: str = "o200k_base") -> float | None:
    try:
        import tiktoken
        enc = tiktoken.get_encoding(encoding)           # GPT-4o tokenizer
        return len(enc.encode(text)) / (_word_count(text) or 1)
    except Exception:
        return None


def fertility_char(text: str) -> float:
    return len(re.sub(r"\s+", "", text)) / (_word_count(text) or 1)


def evaluate(heldout: Path = HELDOUT) -> dict[str, float | None]:
    """Fertility (tokens/word) across tokenizers, mirroring the 'Tokenizer Tax'
    study (2607.24276): GPT-3.5/4 use cl100k_base, GPT-4o uses o200k_base."""
    text = heldout.read_text(encoding="utf-8")
    return {
        "char baseline": round(fertility_char(text), 3),
        "GPT-3.5/4 (cl100k_base)": round(v, 3) if (v := fertility_tiktoken(text, "cl100k_base")) else None,
        "GPT-4o (o200k_base)": round(v, 3) if (v := fertility_tiktoken(text, "o200k_base")) else None,
        "Marathi-BPE (ours)": round(fertility_our(text), 3),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vocab", type=int, default=2000)
    args = ap.parse_args(argv)

    print(f"training Marathi BPE (vocab={args.vocab}) on {CORPUS.name} "
          f"({_word_count(CORPUS.read_text(encoding='utf-8'))} words)…")
    train(vocab_size=args.vocab)
    print(f"saved -> {OUT.relative_to(ROOT)}\n")

    print(f"fertility on held-out Marathi ({_word_count(HELDOUT.read_text(encoding='utf-8'))} words)")
    print(f"{'tokenizer':<26}{'tokens/word':>14}")
    print("-" * 40)
    res = evaluate()
    for name, f in res.items():
        print(f"{name:<26}{(f if f is not None else 'n/a'):>14}")
    gpt, ours = res["GPT-4o (o200k_base)"], res["marathi-bpe (ours)"]
    if gpt and ours:
        print(f"\nOur tokenizer uses {gpt / ours:.2f}x FEWER tokens per word than GPT-4o's.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
