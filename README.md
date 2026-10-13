# Marathi Grounded Report Generator

A system that writes administrative reports in Marathi from a subject and a few
details, where every number is traceable to its source, generated natively in Marathi
without translating through English, and exported as a compile-ready LaTeX document.

This README is written as a walkthrough. Read it top to bottom and each question
answers the next.

---

## The Vision (why this exists)

In a Gram Panchayat office, or for a Tier-3 Marathi speaker filling a government form,
a report today is either handwritten or drafted in English and then translated. That
costs time, drifts in terminology, and quietly distorts numbers. The people who read
these reports are Marathi-first, but the tools that could speed the work up are
English-first.

Our goal is to let a clerk type a handful of facts in plain form (village, households,
funds received, funds spent, works done) and get back a complete, formally worded
Marathi report in seconds, with a guarantee that no figure was invented. The report
comes out as a clean LaTeX document ready to print or submit.

The core promise to the Gram Panchayat user: you give the numbers, the system does the
writing, and you can trust every number in the output because each one is tied back to
what you entered. It never makes up a figure, because a wrong figure in a subsidy or
yield report has real consequences for real people.

---

## Q1. What is the Problem Statement?

Marathi is the official language of Maharashtra, but structured reporting (Gram
Panchayat activity reports, agricultural advisories, district health filings) is mostly
handwritten or written in English and translated. We want to generate these reports
natively in Marathi from structured input, in the correct formal register, with every
numeric claim traceable to a source record, so that the output can be trusted without
manual re-checking of each number.

Formally: given a subject and a set of label to value facts, produce a
template-faithful administrative report in Marathi in which every number is grounded in
a source field.

## Q2. Why is this hard with current tools?

1. Hallucination is unacceptable here, but free-form LLMs invent plausible numbers. In
   our tests, GPT-4o writing Marathi reports freely left about 37 percent of its numbers
   unsupported (not present in the input).
2. Devanagari fragments under English-first tokenizers, which raises cost and can hurt
   quality. This is a measured, published effect (the tokenizer tax).
3. There is no standard administrative-Marathi register, so models drift between formal,
   colloquial, and code-mixed Marathi-English.
4. The common workaround, write in English then machine-translate, adds delay and can
   distort the very numbers that must stay exact.

## Q3. Which paper is central to our approach?

**SymGen: Towards Verifiable Text Generation with Symbolic References** (Torroba
Hennigen, Shen, Nrusimha, Gapp, Sontag, Kim; MIT and Good Data Initiative; COLM 2024;
arXiv:2311.09188; symgen.github.io).

SymGen prompts the model to write Jinja-style `{{ field }}` references into the data
instead of raw values, and a parser substitutes the real values afterward, so every span
links back to a source field. Our pipeline uses exactly this mechanism. What SymGen
reports (confirmed from its tables): symbolic-reference accuracy of 99.77 percent
(GPT-3.5) and 99.52 percent (GPT-4) versus 35 to 46 percent for a regex baseline, and a
human study where provenance annotations cut verification time by about 20 percent
(1.98 vs 2.50 minutes) with roughly unchanged accuracy.

SymGen's own stated limit is that a correct reference can still sit in a wrong sentence,
so it aids human verification rather than enforcing correctness. We build directly on
SymGen and close that gap for numeric claims.

## Q4. How does our approach differ from SymGen?

1. Low-resource target: Marathi and Devanagari, not English.
2. Enforced faithfulness: we add a verifier that rejects any number not bound to a source
   field, so faithfulness is enforced automatically rather than only made easier to check
   by a human.
3. A tokenizer study trained on real Marathi, with Indic-aware baselines.
4. A 500-report scale audit, where SymGen's studies use tens of examples.

## Q5. What exactly does the system do, step by step?

The pipeline has five components (in `pipeline/`):

1. Parse: each detail becomes a typed record with a stable source id (F1, F2, ...).
2. Ground: each report section is bound to the exact fields it may use, before any text
   is generated.
3. Generate: the LLM (GPT-4o) writes the Marathi report using `{{placeholder}}` tokens
   for every value, never a raw number. This is SymGen's Direct symbolic generation.
4. Resolve: each placeholder is substituted with its value and its source id, so every
   figure is traceable by construction.
5. Verify: a checker scans the output and flags or rejects any number that is not bound
   to a source field.

The output is shown on screen with every figure highlighted and linked to its source,
and exported as a LaTeX document.

## Q6. Which datasets did we use, and how large are they?

| Dataset | Purpose | Size |
|---|---|---|
| Marathi Wikipedia (`wikimedia/wikipedia` 20231101.mr) | Train the Marathi tokenizer | 10.2M words |
| Wikipedia held-out (articles never seen in training, split by article hash) | Evaluate tokenizer fertility on general Marathi | 60,046 words, 1,600 paragraphs |
| Synthetic Gram Panchayat benchmark (`data/benchmark_large/reports.csv`) | Faithfulness audit at scale | 500 reports |
| Small evaluation benchmark (`data/benchmark/`) | B1/B2/B4 ablation | 10 reports with gold |
| Administrative held-out (`data/corpus/eval_heldout.txt`) | Indicative only, too small for a claim | 49 words |

Honest note: the Gram Panchayat report benchmarks are synthetic (we generated them).
They test the pipeline and the verifier at scale, but they are not real government
records. The tokenizer is trained and evaluated on real Marathi Wikipedia.

## Q7. What techniques did we use, and what did each one give us?

### Technique 1: Symbolic grounding plus a hard verifier (the main method)

The generator emits `{{field}}` references; we resolve them and then reject any number
that is not bound to a source field. Faithfulness is the fraction of numbers in the
report that trace back to the input.

Experiment A, 10-report ablation (same model, different scaffolding):

| System | Faithfulness | chrF++ | Code-mix | Avg tokens |
|---|---|---|---|---|
| B2, deterministic template | 1.000 | 0.993 | 0.000 | 38 |
| B1, ungrounded LLM (control) | 0.629 | 0.406 | 0.000 | 120 |
| B4, grounded and verified (ours) | 1.000 | 0.454 | 0.000 | 33 |

Result: ungrounded generation leaves about 37 percent of numbers unsupported; our
grounded and verified system reaches zero invented figures and is more concise.

### Technique 2: Model-independence check

Experiment B, same test across two models:

| Generator | B1 ungrounded | B4 grounded (ours) |
|---|---|---|
| GPT-4o | 0.588 | 1.000 |
| GPT-4o-mini | 0.831 | 1.000 |

Result: ungrounded hallucination varies by model, but grounding reaches 1.000 on every
model, so the method does not depend on a particular LLM.

### Technique 3: Scale audit

Experiment D, 500 synthetic reports:

- Faithfulness over all 500 reports: 1.000 (zero unsupported figures). The verifier
  holds at scale, not only on hand-picked examples.
- Ungrounded vs grounded on a 20-report LLM sample: 0.871 to 1.000.
- Token cost on template text (indicative only): the Marathi tokenizer encodes the 500
  template reports in 33,558 tokens vs GPT-4o's 58,350. Because the reports come from one
  template this is an in-template figure, not general efficiency, and generation still
  uses GPT-4o's tokenizer.

### Technique 4: A Marathi tokenizer trained on real data

We trained a Byte-Pair Encoding tokenizer from scratch (not fine-tuned) with HuggingFace
`tokenizers`, NFC normalisation, whitespace pre-tokenization, 32,000 vocabulary entries,
on 10.2M words of real Marathi Wikipedia. We measured fertility (tokens per word, lower
is better) on 60,046 held-out words with 95 percent bootstrap confidence intervals, and
compared against general-purpose and Indic-aware tokenizers.

Experiment C, fertility on held-out Marathi Wikipedia:

| Tokenizer | Vocab | Fertility | 95% CI |
|---|---|---|---|
| GPT-3.5 / GPT-4 (cl100k_base) | 100k | 7.20 | [7.16, 7.23] |
| char baseline | n/a | 5.94 | [5.91, 5.97] |
| GPT-4o (o200k_base) | 200k | 2.67 | [2.65, 2.68] |
| XLM-R | 250k | 2.07 | [2.05, 2.08] |
| IndicBERTv2 | 250k | 1.60 | [1.59, 1.61] |
| MuRIL | 197k | 1.56 | [1.55, 1.57] |
| Marathi-BPE (ours) | 32k | 1.47 | [1.46, 1.48] |

Result: English-first GPT tokenizers pay a large Marathi tax (cl100k is worse than
character-level; o200k is about 1.8 times ours). Against Indic-aware tokenizers the
picture is honest: ours is only about 6 percent below MuRIL and IndicBERTv2, and ours is
trained and tested on the same genre (Wikipedia) while theirs are trained on broader
text, so treat those last rows as roughly a tie. Our tokenizer's unknown-token rate on
the held-out set is 0.016 percent, so it genuinely covers unseen text rather than
memorising a template.

## Q8. What are the headline results?

- Faithfulness: zero invented numbers in grounded generation (1.000), at 10 reports and
  at 500 reports, versus 0.629 for the same model generating freely.
- Model-independent: grounding reaches 1.000 faithfulness on both GPT-4o and GPT-4o-mini.
- Register: code-mixing rate 0.000 (no English slipping into the Marathi).
- Tokenizer: 1.47 tokens per word on general Marathi Wikipedia, below every baseline we
  tested, with tight confidence intervals and a 0.016 percent unknown rate.
- Output: a compile-ready XeLaTeX document with grounded figures marked.

## Q9. What are the honest limitations?

- The Gram Panchayat benchmarks are synthetic, not real government records.
- The tokenizer is trained and tested on the same genre (Wikipedia); a fully fair test
  would use non-Wikipedia Marathi (news, administrative text).
- The tokenizer is a measurement, not part of generation: GPT-4o generates with its own
  tokenizer, so our tokenizer does not change the pipeline's generation cost.
- chrF here is measured against template-style gold, so it understates fluency;
  faithfulness is the defensible headline metric.
- Ungrounded hallucination is probabilistic; 0.629 is an average over reports.

Next steps: real Gram Panchayat data, native-Marathi human evaluation, an
English-then-translate (B0) baseline, and tokenizer evaluation on non-Wikipedia Marathi.

## Q10. How is this grounded in the literature?

- SymGen (COLM 2024, arXiv:2311.09188): our central method, symbolic references.
- IndicGenBench (Google Research India, 2024, arXiv:2404.16816): frontier models still
  lag on Marathi generation (GPT-4 summarization chrF 22.4 Marathi vs 30.3 English), and
  it reports chrF, not BLEU, because token metrics are unreliable for low-resource
  languages.
- The Tokenizer Tax (arXiv:2607.24276): Marathi fertility tax vs English is 5.84 times
  (cl100k) and 2.11 times (o200k); a language-aware tokenizer nearly erases it.
- IndicNLG Benchmark (Kumar et al., EMNLP 2022, arXiv:2203.05437): the first Indic NLG
  benchmark, 5 tasks across 11 languages, including data-to-text from Wikipedia infoboxes,
  the task family our work sits in.
- IndicTrans2 (Gala et al., TMLR 2023, arXiv:2305.16307): the open MT system a
  translate-pivot baseline would use, which our native-generation approach avoids.
- Related faithfulness and low-resource data-to-text work: Faithful Low-Resource
  Data-to-Text through Cycle Training (ACL 2023, arXiv:2305.14793); Guided Beam Search for
  low-resource data-to-text (INLG 2023); Survey of Hallucination in NLG (arXiv:2202.03629).

---

## Run it

```bash
# Backend and pipeline
uv venv -p 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env            # add your OPENAI_API_KEY

# One report from the CLI (offline deterministic engine works without a key)
.venv/bin/python -m pipeline.cli data/sample/gram_panchayat_sample.csv

# Fetch real Marathi Wikipedia, then train and benchmark the tokenizer
.venv/bin/python -m scripts.fetch_marathi_wiki
.venv/bin/python -m pipeline.train_tokenizer

# Faithfulness evaluation (B1 / B2 / B4)
.venv/bin/python -m eval.run_eval

# Backend server
.venv/bin/uvicorn server.app:app --port 8000
```
```bash
# Frontend (new terminal)
cd frontend && npm install && npm run dev      # http://localhost:5173
```

The web app: New report (enter subject and details), Generate, then Results (live
grounded vs ungrounded comparison, scale audit, tokenizer comparison, and literature).
About the method explains the full approach. The generated report.tex compiles with
XeLaTeX.

## Repo layout
```
pipeline/   the NLP system: parse, ground, generate, resolve, verify, report
            and train_tokenizer.py (trains and benchmarks the Marathi tokenizer on real Wikipedia)
server/     FastAPI backend (/api/report, /api/report/compare, /api/generate)
eval/       metrics, B1/B2/B4 harness, RESULTS.md, tokenizer_results.json, audit.json
frontend/   React (Vite) app, the two-screen demo
latex/      XeLaTeX template (Noto Serif Devanagari) for the .tex output
lexicon/    domain terminology bank (register control)
data/       benchmarks and corpora (Gram Panchayat benchmarks are synthetic; corpus is real Wikipedia)
figures/    charts (make_figures.py, make_audit_figure.py)
scripts/    data generation and the Wikipedia fetch/split
plan.md     the detailed, paper-grounded NLP plan
```
