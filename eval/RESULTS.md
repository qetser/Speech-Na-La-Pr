# Evaluation Results

Benchmark: 10 Gram Panchayat activity reports (`data/benchmark/gp01..gp10`).
Generator for B1/B4: OpenAI `gpt-4o`. Run via `python -m eval.run_eval`.

| System | Faithfulness | chrF++ | Code-mix | Token cost | n |
|---|---|---|---|---|---|
| **B2** deterministic (grounded + structured) | **1.000** | 0.993 | 0.000 | 38.1 | 10 |
| **B1** ChatGPT, ungrounded, no verifier *(control)* | **0.629** | 0.406 | 0.000 | 120.2 | 10 |
| **B4** ChatGPT, grounded + verified *(ours)* | **1.000** | 0.454 | 0.000 | 32.7 | 10 |

`faithfulness` = fraction of numbers in the report that trace back to a source cell
(1.000 = zero hallucinated/unsupported figures).

## What this shows
- **The problem is real.** An unconstrained LLM writing Marathi reports (B1) leaves
  **37% of its numbers unsupported** (faithfulness 0.629) — fabricated or distorted
  figures that are not in the source data.
- **Our system fixes it.** The same model, constrained to symbolic placeholders and
  checked by the verifier (B4), reaches **1.000 faithfulness** — zero hallucinated
  numbers — while staying native Marathi with no code-mixing (0.000).
- **It is also cheaper.** B4 is more concise than B1 (32.7 vs 120.2 tokens): grounding
  focuses the model instead of letting it pad.

## Tokenizer study (Component 2 — a measurement; not used in generation)

BPE (vocab 32,000, all filled) trained on 10.2M words of real Marathi Wikipedia
(`pipeline/train_tokenizer.py`); evaluated on 60,046 words from held-out *articles*
(general Marathi). Full numbers: `eval/tokenizer_results.json`.

| Tokenizer | Fertility (tokens/word), 95% CI |
|---|---|
| char baseline | 5.94 |
| GPT-3.5/4 (cl100k) | 7.20 [7.16, 7.23] |
| GPT-4o (o200k) | 2.67 [2.65, 2.68] |
| XLM-R | 2.07 [2.05, 2.08] |
| MuRIL | 1.56 [1.55, 1.57] |
| IndicBERTv2 | 1.60 [1.59, 1.61] |
| **Marathi-BPE (ours)** | **1.47 [1.46, 1.48]** |

**Finding:** GPT tokenizers pay a large Marathi tax (o200k ≈ 1.8× ours; cl100k worse than
characters). Against Indic-aware tokenizers ours is only ~6% lower — near a tie, and ours
shares its genre (Wikipedia) with the test set. The tokenizer does **not** affect
generation cost: GPT-4o generates with its own tokenizer.

*Superseded:* the earlier 1.6k-word template-corpus result (2.18 vs 2.80 on 49 words)
was too small and too close to its training text to support a claim.

## Scale audit — 500-report synthetic benchmark

Generated `data/benchmark_large/reports.csv` (500 template rows). Results:

- **Deterministic faithfulness over all 500 reports: 1.000** (zero unsupported figures).
- **Template-text token cost:** ours 33,558 vs GPT-4o 58,350 tokens (1.74×) — indicative
  only, since all reports share one template.
- **Ungrounded vs grounded (sample of 20 LLM runs):** B1 **0.871** → B4 **1.000**.

See `figures/fig6_scale_audit.png` (generated from `eval/audit.json`).

## Across models — grounding is model-independent

B1 (ungrounded) vs B4 (grounded, ours), faithfulness over 3 reports each:

| Generator | B1 ungrounded | B4 grounded (ours) |
|---|---|---|
| GPT-4o | 0.588 | **1.000** |
| GPT-4o-mini | 0.831 | **1.000** |

Ungrounded hallucination varies by model; grounding + verification reaches 1.000 on
every model tested. The method does not depend on a particular LLM.

## Tokenizer fertility

See the Tokenizer study section above (held-out Wikipedia, with Indic baselines).

## What the base papers report (for positioning)

- **IndicGenBench** (Google Research, 2404.16816): frontier models still lag badly on
  Marathi generation — GPT-4 summarization chrF **22.4 (mr) vs 30.3 (en)**; PaLM-2-L
  25.4 vs 41.1. The benchmark reports **chrF, not BLEU**, stating token metrics "are not
  reliable for low-resource languages" — directly supporting our metric choice.
- **The Tokenizer Tax** (2607.24276): Marathi word-fertility tax vs English is 9.04×
  (GPT-2), 5.84× (cl100k), 2.11× (o200k), 1.41× (XLM-R). A language-aware tokenizer
  nearly erases the tax — the trajectory our trained tokenizer follows.

## Honest caveat on chrF
The gold reports are the canonical **template** phrasing (= B2's output), so B2 scores
~0.99 by construction and the LLM systems score lower because they phrase validly but
differently. chrF here measures *distance from the template*, not fluency. The headline,
defensible metric is **faithfulness**; a fair fluency comparison needs LLM-written or
human-written gold and native-Marathi human ratings (next step).
