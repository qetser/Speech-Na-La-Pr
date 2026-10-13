# Marathi Grounded Report Generator

**Generate official-style reports in Marathi from a subject + a few details, where
every number is traceable to its source — natively, without translating through
English — and export a compile-ready LaTeX document.**

An NLP project on *retrieval-grounded, structure-constrained generation* for a
low-resource, morphologically rich language.

> **Core method — SymGen.** This project applies *symbolically grounded generation*
> (**SymGen**; Torroba Hennigen, Shen, Nrusimha, Gapp, Sontag & Kim — MIT & Good Data
> Initiative, **COLM 2024**, [arXiv:2311.09188](https://arxiv.org/abs/2311.09188),
> [symgen.github.io](https://symgen.github.io)) to Marathi administrative reports.
> SymGen has the LLM emit `{{ field }}` references into the source data instead of raw
> values, which a parser then renders — **exactly the mechanism our pipeline uses.** We
> extend it to a low-resource language, add a hard verifier that *rejects* ungrounded
> numbers, train a Marathi tokenizer, and test at scale. See §8.

---

## 1. Problem Statement

Marathi is the official language of Maharashtra, yet almost every structured
reporting workflow in the state — Gram Panchayat activity reports, agricultural
advisories, district health filings — is either handwritten or **drafted in English
and translated afterwards**. The result is delay, inconsistent terminology, and a
loss of meaning exactly where it matters most: at the Marathi-first reader.

**The task, stated precisely:** given a subject and a set of structured details
(label → value facts), produce a template-faithful administrative report in Marathi
in which **every numeric claim is traceable back to a source detail**, generated
natively in Marathi.

---

## 2. Why this is hard (what currently goes wrong)

Current LLMs handle this poorly for three concrete reasons:

1. **Hallucination is unacceptable here.** A single fabricated figure in a subsidy
   or yield report has real consequences. But free-form LLMs *invent* plausible
   numbers. In our own tests, GPT-4o writing Marathi reports freely left **~37% of
   its numbers unsupported** (not present in the source data).

2. **Devanagari fragments under standard tokenizers.** Tokenizers are trained
   mostly on English, so they shatter Marathi into many tokens — raising cost and
   lowering quality. This is a published, measured effect (the "tokenizer tax").

3. **No standardized register.** Models drift between formal Sanskritised Marathi,
   colloquial speech, and code-mixed Marathi-English, because there is no agreed
   lexicon for administrative/agri-technical Marathi.

And the common workaround — **write in English, then machine-translate to Marathi**
— adds its own delay and distortion, and still isn't faithful to the source numbers.

---

## 3. Our Solution

A pipeline that **grounds** generation in the input and **verifies** it before
output:

- **You give:** a subject, a report type, and a few `label → value` details (plus
  optional context notes).
- **The system writes** a full multi-section report in Marathi, but the generator
  is *constrained*: it must write every value as a `{{placeholder}}` token, never a
  raw number.
- **We substitute** each placeholder with its real value and tag it with a source
  id → every figure is traceable **by construction**.
- **A verifier** scans the output and flags any number that isn't backed by a
  source detail.
- **Output:** the Marathi report on screen (figures highlighted + linked to source)
  and a compile-ready **XeLaTeX** document.

It runs as a CLI, a FastAPI backend, and a React web app.

---

## 4. Why this is better

| vs. … | Why ours wins |
|---|---|
| **Raw LLM (ungrounded)** | It hallucinates figures; we drive unsupported numbers to **zero** via grounding + verification. |
| **English → translate pivot** | We generate **natively in Marathi** — no translation step to add delay or distort numbers. |
| **A fixed template / mail-merge** | We produce fluent, multi-section prose that adapts to the subject, yet stays grounded. |
| **English-centric tokenizer** | Our trained Marathi tokenizer encodes the same text in far fewer tokens (see §6). |

The key idea: **faithfulness is guaranteed by construction (symbolic placeholders),
not by hoping the model behaves.**

---

## 5. How we built it — the pipeline

Five components (`pipeline/`):

1. **Parse** — each detail becomes a typed record with a stable source id (`F1`, `F2`…).
2. **Ground** — each report section is bound to the exact details it may use, *before* any text is generated.
3. **Generate** — the LLM (GPT-4o) writes the Marathi report using `{{placeholder}}` tokens for every value.
4. **Resolve** — each placeholder is substituted with its value + source id → traceable tokens.
5. **Verify** — every number must map to a source detail; stray numbers are flagged as unsupported.

Steps 3–4 are **SymGen's "Direct" symbolic generation** (arXiv:2311.09188): the model
emits `{{ field }}` references and a parser renders them. Step 5 is our addition — a
hard verifier that *rejects* any number not bound to a source field, so faithfulness is
*enforced*, not merely made easier to check by hand.

---

## 6. The tokenizer — why, how we trained it, and results

**Why.** Standard LLM tokenizers over-fragment Devanagari, which raises cost and can
hurt quality. We wanted to *measure* this and show a specialized tokenizer helps.

**How we built it** (note: a tokenizer is **trained from scratch**, not fine-tuned):
- Algorithm: **Byte-Pair Encoding (BPE)** via the HuggingFace `tokenizers` library.
- Normalization: **NFC** (canonical Devanagari); pre-tokenization on whitespace.
- Vocabulary: **2,000**; `min_frequency = 2`.
- Training corpus: ~**1,650 words** of administrative/agri Marathi.
- Evaluated on a **held-out** Marathi set (kept out of training) using **fertility**
  = tokens per word (lower is better).

Command: `python -m pipeline.train_tokenizer`

**Results — fertility (tokens/word) on held-out Marathi:**

| Tokenizer | Fertility | vs ours |
|---|---|---|
| char baseline | 6.76 | 3.1× |
| GPT-3.5 / GPT-4 (`cl100k_base`) | **7.98** | 3.7× |
| GPT-4o (`o200k_base`) | 2.80 | 1.3× |
| **Marathi-BPE (ours, trained)** | **2.18** | 1.0× |

GPT-3.5/4's tokenizer is *worse than character-level* on Marathi. Our tokenizer is
**3.7× more efficient than GPT-3.5/4** and **1.3× more than GPT-4o**.

![Tokenizer fertility on Marathi](figures/fig3_tokenizer_fertility.png)

---

## 7. What we tested, and what we found

**Experiment A — does grounding stop hallucination?** (B1→B4 ablation)
Same model, different scaffolding, over a 10-report benchmark:

| System | Faithfulness | chrF++ | Code-mix | Avg tokens |
|---|---|---|---|---|
| B2 · deterministic template | 1.000 | 0.993 | 0.000 | 38 |
| **B1 · ungrounded LLM (control)** | **0.629** | 0.406 | 0.000 | 120 |
| **B4 · grounded + verified (ours)** | **1.000** | 0.454 | 0.000 | 33 |

→ Ungrounded leaves **37% of numbers unsupported**; grounded reaches **zero invented
figures**, and is more concise.

![Ablation: faithfulness B1 vs B2 vs B4](figures/fig2_ablation.png)

**Experiment B — does it depend on the model?** (B1 vs B4 across models)

| Generator | B1 ungrounded | B4 grounded (ours) |
|---|---|---|
| GPT-4o | 0.588 | **1.000** |
| GPT-4o-mini | 0.831 | **1.000** |

→ Ungrounded hallucination varies by model; **grounding reaches 1.000 on every
model** — the method is model-independent.

![Faithfulness across models](figures/fig1_models_faithfulness.png)

**Experiment C — tokenizer fertility** → see §6.

**Experiment D — does it hold at scale?** (500-report audit)
We generated a **500-report synthetic benchmark** (`data/benchmark_large/`) and audited it:

- **Faithfulness over all 500 reports: 1.000** (zero unsupported figures) — the
  verifier holds at scale, not just on cherry-picked examples.
- **Token cost:** our tokenizer encodes the 500 reports in **29,983 tokens vs GPT-4o's
  58,350 — a 1.95× saving** on real in-domain text.
- **Ungrounded vs grounded (sample of 20 LLM runs):** B1 **0.871** → B4 **1.000**.

![Scale audit over 500 reports](figures/fig6_scale_audit.png)

*Left:* our tokenizer encodes every report in roughly half the tokens of GPT-4o's.
*Middle:* a faithfulness audit — grounded (B4) sits flat at 1.0 while ungrounded (B1)
drops wherever the model invented a figure. *Right:* per-report token counts, ours vs
GPT-4o, every point below the parity line.

**Metrics beyond BLEU.** BLEU correlates poorly for inflectional low-resource
languages, so we report **faithfulness** (our headline), **chrF++**, **code-mix
rate**, and token cost.

---

## 8. How this sits in the literature — what the base papers built & found

### ★ SymGen — our central paper (COLM 2024 — arXiv:2311.09188)
*Torroba Hennigen, Shen, Nrusimha, Gapp, Sontag & Kim (MIT & Good Data Initiative).*

**What they built:** *symbolically grounded generation* — instead of writing values
directly, the LLM is prompted to interleave its text with **Jinja-like `{{ field }}`
references** into structured data, and a parser substitutes the real values afterward.
This gives every span a verifiable provenance. They study it across data-to-text
(SynthBio, Rotowire), counterfactual obituaries, financial QA, and GSM8K math.

**What they found (confirmed from the paper's tables):**
- **Symbolic references are highly accurate:** reference accuracy **99.77%** (GPT-3.5-16K)
  and **99.52%** (GPT-4-32K), versus only **35.4% / 46.1%** for a regex post-hoc baseline
  (9,068 human annotations, 97.8% agreement).
- **No quality loss:** rendered text is comparable in fluency/factuality to standard prompting.
- **Easier verification (human study, 60 annotators):** annotations cut verification
  **time ~20%** (1.98 vs 2.50 min), made it feel 14% easier; 83% preferred them.
- **Stated limitation:** accurate references don't guarantee the *surrounding prose* is
  correct — SymGen *aids* human verification, it does not *enforce* correctness.

**How our project extends SymGen:**
1. **Low-resource target** — Marathi / Devanagari, not English.
2. **Enforced faithfulness** — we add a hard verifier that *rejects* any number not bound
   to a source field, directly closing SymGen's "context may still be wrong" gap for
   numeric claims (their human-aided check becomes our automatic gate).
3. **A trained Marathi tokenizer** — addressing the Devanagari tokenizer tax.
4. **Scale** — a 500-report audit (SymGen's studies use tens of examples).
   This also follows their own suggested future work ("finetune models for templated
   generation").

### IndicGenBench (Google Research India, 2024 — arXiv:2404.16816)
**What they built:** the largest benchmark for evaluating LLM *generation* on Indic
languages — **29 languages, 13 scripts, 4 families**, across five human-curated,
multi-way-parallel tasks: cross-lingual summarization (CrossSum-IN), machine
translation (FLORES-IN), multilingual QA (XQuAD-IN), and cross-lingual QA
(XORQA-IN). Marathi is one of the covered languages.

**What they found:**
- They benchmarked GPT-3.5, GPT-4, PaLM-2, mT5, Gemma, BLOOM/BLOOMZ, LLaMA.
  **PaLM-2-L was best overall**; open models (LLaMA) lagged proprietary ones badly.
- A **large, consistent English↔Indic gap** (often 20+ points) remains even for
  frontier models. For Marathi summarization: **GPT-4 chrF 22.4 vs 30.3 English**;
  PaLM-2-L 25.4 vs 41.1.
- They deliberately report **chrF, not BLEU/ROUGE**, stating token metrics "are not
  reliable for low-resource languages" — which independently validates our metric choice.

![IndicGenBench: Marathi vs English chrF](figures/fig5_paper_indicgenbench.png)

### The Tokenizer Tax (2026 — arXiv:2607.24276)
**What they built:** a content-controlled measurement (on FLORES-200) of the
"tokenizer tax" — fertility relative to English — across **10 Indian languages and 6
tokenizers**, plus a mechanistic explanation and a remediability analysis.

**What they found:**
- The Marathi word-fertility tax vs English is **9.04× (GPT-2), 5.84× (cl100k =
  GPT-3.5/4), 2.11× (o200k = GPT-4o), 1.41× (XLM-R)**; mean Indic tax **8.0×**, up to
  13× for Malayalam.
- **Cause:** failed BPE merges leave Devanagari stranded as single bytes (correlates
  with the tax at r = 0.89).
- **It's a design choice, not the script's fault:** a language-aware tokenizer nearly
  erases the tax, and o200k already cut the mean Indic tax **73%** vs cl100k.

![Base paper: Marathi tokenizer tax](figures/fig4_paper_tokenizer_tax.png)

**Why this matters for us:** both papers establish the exact gaps we target — frontier
models underperform on Marathi, BLEU is the wrong metric, and standard tokenizers
overcharge Devanagari. Our trained Marathi tokenizer follows the *same remediation
trajectory* these papers describe.

### Other method foundations
Controlled table-to-text (ToTTo, 2004.14373); plan-based retrieval grounding
(2408.10490); morphology-grounded Indic tokenization (MorphTok, 2504.10335).
(The core symbolic-reference method is SymGen, above.)

---

## 9. Honest limitations (what we do *not* claim)

Stated up front, because they matter:

- **The benchmark is synthetic.** The reports, gold answers, tokenizer corpus, and
  held-out set were generated by us, not drawn from real Gram Panchayat records.
  The *measurements* are real; the *data under them* is not yet real.
- **Our tokenizer is domain-specialized.** It was trained and tested on similar
  administrative Marathi, so its fertility edge is partly an in-domain advantage;
  it is a proof-of-concept of the effect, not a production tokenizer.
- **chrF here is measured against template-style gold**, so it understates the LLM's
  fluency. Faithfulness is the defensible headline metric; a fair fluency number
  needs human raters.
- **Ungrounded hallucination is probabilistic** — 0.629 is an average over reports,
  not a guarantee on any single run.

**Next steps:** real Gram Panchayat data, native-Marathi human evaluation, a
translate-pivot (B0) baseline, and a larger tokenizer corpus.

---

## 10. Run it

```bash
# Backend + pipeline
uv venv -p 3.14 .venv            # or: python3 -m venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env             # add your OPENAI_API_KEY

# CLI — one report (offline deterministic engine works without a key)
.venv/bin/python -m pipeline.cli data/sample/gram_panchayat_sample.csv

# Train the Marathi tokenizer + fertility comparison
.venv/bin/python -m pipeline.train_tokenizer

# Evaluation — the B1 / B2 / B4 results table
.venv/bin/python -m eval.run_eval

# Regenerate the figures in this README
.venv/bin/python figures/make_figures.py

# Backend server
.venv/bin/uvicorn server.app:app --port 8000
```
```bash
# Frontend (new terminal)
cd frontend && npm install && npm run dev      # http://localhost:5173
```
The web app: **New report** (enter subject + details) → **Generate** → **Results**
(live grounded-vs-ungrounded comparison, timing, tokenizer comparison, benchmark,
and literature). **About the method** explains the full approach. The generated
`report.tex` compiles with **XeLaTeX** (or Overleaf → XeLaTeX).

---

## 11. Repo layout
```
pipeline/   the NLP system: parse, ground, generate, resolve, verify, report
            + train_tokenizer.py (trains the Marathi BPE tokenizer)
server/     FastAPI backend (/api/report, /api/report/compare, /api/generate)
eval/       metrics + B1/B2/B4 harness + RESULTS.md + multimodel_results.json
frontend/   React (Vite) app — the two-screen demo
latex/      XeLaTeX template (Noto Serif Devanagari) for the .tex output
lexicon/    domain terminology bank (register control)
data/       benchmark reports, corpus, samples  (synthetic — see §9)
figures/    research-style charts (make_figures.py) embedded in this README
plan.md     the detailed, paper-grounded NLP plan
```

---

*Deliverables: an open Marathi report-generation benchmark, a reusable domain
lexicon, a trained Marathi tokenizer, and a deployable pipeline showing that
grounded generation in a low-resource Indic language eliminates numeric
hallucination — without translation as an intermediate step.*
