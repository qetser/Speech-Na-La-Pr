"""Component 2: train a Marathi BPE tokenizer on REAL Marathi (Wikipedia) and
compare its subword fertility against general-purpose and Indic-aware tokenizers.

Fertility = tokens per word (lower is better: cheaper + usually better quality).

    python -m scripts.fetch_marathi_wiki        # once: real corpus + article-level split
    python -m pipeline.train_tokenizer          # train + evaluate
    python -m pipeline.train_tokenizer --vocab 32000

Evaluation sets (see `evaluate`):
  * heldout_wiki  — ~60k words from Wikipedia ARTICLES never seen in training
                    (general Marathi, not administrative). Headline number.
  * admin_heldout — 49 words of administrative Marathi. Far too small for a
                    claim; kept only as an indication.
Baselines: char, GPT-3.5/4 (cl100k), GPT-4o (o200k), and the Indic-aware
tokenizers XLM-R, MuRIL, IndicBERTv2. 95% CIs are bootstrapped over paragraphs.
NOTE: this tokenizer is NOT used by the generation pipeline (GPT-4o generates with
its own tokenizer); it only measures what a Marathi-native tokenizer would cost.
"""
from __future__ import annotations

import argparse
import random
import re
from pathlib import Path

from tokenizers import Tokenizer, models, normalizers, pre_tokenizers, trainers

ROOT = Path(__file__).resolve().parent.parent
REAL = ROOT / "data" / "corpus" / "real"
CORPUS = REAL / "train_wiki.txt"
HELDOUT = REAL / "heldout_wiki.txt"
ADMIN_HELDOUT = ROOT / "data" / "corpus" / "eval_heldout.txt"
OUT = ROOT / "tokenizers" / "marathi_bpe.json"

HF_BASELINES = {
    "XLM-R": "xlm-roberta-base",
    "MuRIL": "google/muril-base-cased",
    "IndicBERTv2": "ai4bharat/IndicBERTv2-MLM-only",
}

_WORD = re.compile(r"\S+")


def train(corpus: Path = CORPUS, vocab_size: int = 32000, out: Path = OUT) -> Path:
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


def _tokenizers() -> dict:
    """name -> callable(text) -> n_tokens. Unavailable baselines are skipped."""
    fns = {"char baseline": lambda t: len(re.sub(r"\s+", "", t))}
    try:
        import tiktoken
        for name, enc in (("GPT-3.5/4 (cl100k)", "cl100k_base"), ("GPT-4o (o200k)", "o200k_base")):
            e = tiktoken.get_encoding(enc)
            fns[name] = lambda t, e=e: len(e.encode(t))
    except Exception as exc:
        print(f"[skip tiktoken: {exc}]")
    try:
        from transformers import AutoTokenizer
        for name, hub in HF_BASELINES.items():
            try:
                t = AutoTokenizer.from_pretrained(hub)
                fns[name] = lambda x, t=t: len(t.encode(x, add_special_tokens=False))
            except Exception as exc:
                print(f"[skip {name}: {type(exc).__name__}]")
    except ImportError:
        print("[skip HF baselines: transformers not installed]")
    ours = Tokenizer.from_file(str(OUT))
    fns["Marathi-BPE (ours)"] = lambda t: len(ours.encode(t).tokens)
    return fns


def _fert(fn, paras: list[str]) -> float:
    return sum(fn(p) for p in paras) / (sum(_word_count(p) for p in paras) or 1)


def _bootstrap_ci(fn, paras: list[str], n: int = 200, seed: int = 0) -> tuple[float, float]:
    """95% CI of corpus fertility, resampling paragraphs (per-paragraph counts cached)."""
    rng = random.Random(seed)
    toks = [fn(p) for p in paras]
    words = [_word_count(p) for p in paras]
    idx = range(len(paras))
    stats = []
    for _ in range(n):
        s = [rng.choice(idx) for _ in idx]
        stats.append(sum(toks[i] for i in s) / (sum(words[i] for i in s) or 1))
    stats.sort()
    return stats[int(0.025 * n)], stats[int(0.975 * n) - 1]


def evaluate(heldout: Path = HELDOUT, admin: Path = ADMIN_HELDOUT, ci: bool = True) -> dict:
    """{set_name: {"words": int, "fertility": {tokenizer: (mean, lo, hi)}}}."""
    sets = {"heldout_wiki": heldout, "admin_heldout": admin}
    fns = _tokenizers()
    res: dict = {}
    for sname, path in sets.items():
        if not path.exists():
            continue
        paras = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        entry = {"words": sum(_word_count(p) for p in paras), "paragraphs": len(paras), "fertility": {}}
        for name, fn in fns.items():
            m = _fert(fn, paras)
            lo, hi = _bootstrap_ci(fn, paras) if ci and len(paras) >= 20 else (None, None)
            entry["fertility"][name] = (round(m, 3), lo and round(lo, 3), hi and round(hi, 3))
        res[sname] = entry
    return res


def unk_rate(path: Path = HELDOUT) -> float:
    tok = Tokenizer.from_file(str(OUT))
    toks = [t for l in path.read_text(encoding="utf-8").splitlines() if l.strip()
            for t in tok.encode(l).tokens]
    return sum(t == "<unk>" for t in toks) / (len(toks) or 1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vocab", type=int, default=32000)
    ap.add_argument("--skip-train", action="store_true")
    args = ap.parse_args(argv)

    if not CORPUS.exists():
        raise SystemExit("missing real corpus - run: python -m scripts.fetch_marathi_wiki")
    if not args.skip_train:
        print(f"training Marathi BPE (vocab={args.vocab}) on {CORPUS.name} "
              f"({_word_count(CORPUS.read_text(encoding='utf-8')):,} words)...")
        train(vocab_size=args.vocab)
        print(f"saved -> {OUT.relative_to(ROOT)}  (vocab entries: "
              f"{Tokenizer.from_file(str(OUT)).get_vocab_size()})")

    res = evaluate()
    for sname, e in res.items():
        print(f"\n{sname}: {e['words']:,} words, {e['paragraphs']} paragraphs")
        print(f"{'tokenizer':<24}{'tokens/word':>12}   95% CI")
        print("-" * 52)
        for name, (m, lo, hi) in e["fertility"].items():
            print(f"{name:<24}{m:>12}   " + (f"[{lo}, {hi}]" if lo else "(too small for a CI)"))
    import json
    (ROOT / "eval" / "tokenizer_results.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nour <unk> rate on held-out wiki: {unk_rate():.4%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
