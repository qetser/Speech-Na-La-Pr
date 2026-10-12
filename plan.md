# Concrete NLP Plan — Marathi Grounded Report Generation

**Subject:** Natural Language Processing
**Task type (how NLP frames this):** *Controlled, retrieval-grounded data-to-text (table-to-text) generation in a low-resource, morphologically rich language, with a faithfulness-verification layer and register control.*
**Date:** 2026-10-12

This is the "how we actually do it" document. Every design choice below is tied
to a specific published method so we are building on known results, not guessing.
(IDs are arXiv/alphaXiv; open as `https://www.alphaxiv.org/abs/<ID>`.)

---

## 0. The task, stated precisely

> Given a source table `T` (rows = records, columns = typed fields) and a fixed
> report template `S` (ordered slots, each slot = a sentence/para schema with
> typed placeholders), produce a Marathi report `R` such that:
>   (a) `R` is template-faithful (follows `S`'s structure and ordering),
>   (b) every numeric/entity claim in `R` is **traceable** to a cell in `T`
>       (no hallucinated figures),
>   (c) `R` is in the target **register** (formal administrative / agri-technical
>       Marathi), with controlled code-mixing.

This is exactly the **controlled table-to-text** formulation of ToTTo
(2004.14373), extended with (b) a verification layer and (c) register control.

---

## 1. System architecture (6 NLP components)

```
 CSV / form / survey
        │
        ▼
 [1] Input normalization & schema parsing      ──► typed records {field: (value, unit, source_cell_id)}
        │
        ▼
 [2] Tokenization / morphology layer           ──► Marathi-aware subword segmentation
        │
        ▼
 [3] Content selection + retrieval grounding    ──► for each template slot, the exact source cells it may use
        │
        ▼
 [4] Structure-constrained generation           ──► slot-filled Marathi text (blueprint / plan-then-generate)
        │
        ▼
 [5] Faithfulness verification layer            ──► every number/entity checked back to T; unsupported claims blocked/flagged
        │
        ▼
 [6] Evaluation harness (automatic + human)     ──► faithfulness, register, fluency, cost
```

Each component below lists: **method → paper → what we build.**

---

### Component 1 — Input normalization & schema parsing
- **Method:** schema-guided parsing; treat each cell as a grounded unit with a
  stable `source_cell_id` (this id is what the verifier checks against later).
- **Papers:** Map&Make / schema-guided text↔table (2505.23174); ToTTo cell
  highlighting (2004.14373).
- **Build:** a loader that turns CSV/form rows into typed records
  `{field, value, unit, source_cell_id}`, plus a template spec `S` in YAML/JSON
  (ordered slots, each declaring which fields it consumes).

### Component 2 — Tokenization / morphology (the low-resource core)
- **Why it matters:** standard tokenizers fragment Devanagari badly → higher
  cost, worse quality. We must *measure* this, not assume it.
- **Papers:**
  - MorphTok — morphologically grounded tokenization for Indian languages (2504.10335)
  - BHARATI — morphology-aware tokenizers + subword **fertility** analysis (2607.23319)
  - "Tokenizer Tax" for Indian languages — quantifies the cross-lingual cost (2607.24276)
  - "Multilingual Tokenization through the Lens of Indian Languages" (2506.17789)
  - "Vowel Signs Are Not Letters" — abugida pre-tokenization ceiling (2608.26449)
  - TokEval — tokenizer evaluation suite (2608.18062)
  - "Tokenization Matters: Zero-Shot NER for Indic" (2504.16977)
- **Build / experiment:** measure **fertility (tokens/word)** on our Marathi
  report corpus for each candidate (GPT-style BPE, SentencePiece, MuRIL/IndicBERT,
  MorphTok). Pick the tokenizer with the best fertility-vs-quality tradeoff and
  **report the cost delta**. This is a concrete, publishable finding on its own.

### Component 3 — Content selection + retrieval grounding
- **Method:** retrieval-augmented, plan-based grounding — select the source
  cells relevant to each slot *before* generating, so the model never invents.
- **Papers:**
  - Plan-based retrieval for grounded generation (2408.10490)
  - IndicRAGSuite — Indic-language RAG datasets/benchmark (2506.01615)
  - Conditional generation with a QA blueprint (2207.00397)
- **Build:** a deterministic slot→cell binder (template declares the fields;
  binder resolves them from `T`). For free-text slots, retrieve the supporting
  records. Output: a per-slot "evidence set" passed to generation.

### Component 4 — Structure-constrained generation
- **Method:** plan-then-generate / blueprint generation; constrained decoding so
  output follows the template and only uses bound evidence.
- **Papers:**
  - QA-blueprint conditional generation (2207.00397)
  - Compositional generalization for data-to-text (2312.02748)
  - Tree-of-Text prompting for table-to-text (2604.26501)
  - Survey of neural data-to-text (2207.12571) — design reference
- **Candidate generator models (to benchmark, not assume):**
  - Open Indic LLMs: PARAM-1 / BharatGen 2.9B (2507.13390); Airavata; Gemma/Llama
    Indic fine-tunes; IndicTrans2 only if we test a translate-pivot baseline.
  - Closed APIs (OpenAI GPT) as strong upper-bound baselines.
- **Register control:** inject the domain lexicon (Deliverable D2) + few-shot
  register exemplars; constrain code-mixing. Related: code-mix evaluation
  (Indi-RomCoM 2606.30790) for measuring drift.

### Component 5 — Faithfulness / verification layer (the "no hallucination" guarantee)
- **Method:** symbolic references — generate with placeholders that point to
  `source_cell_id`, then resolve + check; reject/flag any number not backed by a cell.
- **Papers:**
  - Towards Verifiable Text Generation with **Symbolic References** (2311.09188) — core design
  - SCOPE — self-supervised faithfulness improvement (2502.13674)
  - BHRAM-IL — hallucination recognition in Indian languages (2512.01852) — eval
  - "On a Scale from 1 to 5: Quantifying Hallucination in Faithfulness Eval" (2410.12222)
- **Build:** a post-generation checker that (i) extracts every numeric/entity
  claim, (ii) matches it to the bound `source_cell_id`, (iii) blocks, regenerates,
  or flags-for-human on mismatch. Target: **0 unsupported numeric claims**.

### Component 6 — Evaluation (beyond BLEU)
- **Why:** BLEU correlates weakly for inflectional low-resource languages.
- **Papers:**
  - ChrF++ vs BLEU for extremely low-resource MT (2602.17425)
  - Crosslingual Optimized Metric for Indian languages (2509.17667)
  - LLM-as-a-Judge for multilingual / low-resource settings — caveats (2607.02235)
  - Reference-free evaluation metrics survey (2501.12011)
  - IndicGenBench — Indic generation benchmark + protocol (2404.16816)
- **Metric suite (report all):**
  - *Surface:* chrF++ (not BLEU-only), token fertility/cost.
  - *Faithfulness:* % numeric claims traceable (our verifier), hallucination rate.
  - *Register:* lexicon-adherence score + code-mix rate.
  - *Fluency/adequacy:* LLM-as-judge **with** human spot-check (judges are noisy
    in low-resource langs — 2607.02235).
  - *Human:* native Marathi raters on faithfulness + register (the ground truth).
- **Baseline to beat:** the **English-then-translate** pipeline (generate in
  English → MT to Marathi, e.g. IndicTrans2). Our thesis: the **native grounded**
  pipeline matches or beats it *without* translation as an intermediate step.

---

## 2. Data & resources we build on (so we don't start from zero)
- **Marathi corpora / models:** L3Cube MahaNLP family — MahaPOS (2606.24825),
  MahaParaphrase (2508.17444); Marathi NER study (2607.23344); Marathi topic
  modeling (2502.02100).
- **Parallel data (for the translate baseline):** BhashaSetu En–Mr (2605.27050).
- **Resource survey (to find more):** BhashaSutra — unified survey of Indian NLP
  datasets/corpora (2604.18423).
- **Our own data (the deliverable):** (source table → gold Marathi report) pairs
  for ONE pilot domain. This becomes **Deliverable D1 (the benchmark)**.

---

## 3. Baselines & ablations (what makes it a real NLP study)
| # | System | Purpose |
|---|--------|---------|
| B0 | English-then-translate (LLM→IndicTrans2) | the pipeline we claim to beat |
| B1 | Direct Marathi LLM, no grounding, no verify | shows hallucination problem |
| B2 | B1 + retrieval grounding | isolates grounding gain |
| B3 | B2 + structure constraint (blueprint) | isolates template faithfulness gain |
| B4 | B3 + verification layer (full system) | the proposed system |
| Abl | swap tokenizer (standard vs MorphTok) | isolates tokenization effect on cost/quality |

Measuring B0→B4 on the same benchmark is the core experimental contribution.

---

## 4. Milestones (12 weeks, course-project sized)
- **W1 — Scope + data:** pick pilot domain (recommend Gram Panchayat activity
  report), collect 3–10 real templates + sample source tables, define schema `S`.
- **W2–4 — Benchmark v0 + lexicon seed:** build 50–200 (table→gold report) pairs;
  seed the domain lexicon with register tags.
- **W3–5 — Tokenization study (Component 2):** fertility measurements + pick tokenizer.
- **W5–7 — Pipeline v0 (Components 1,3,4):** first end-to-end Marathi reports (B2/B3).
- **W7–9 — Verification layer (Component 5):** symbolic-reference checker; drive
  unsupported-claim rate toward 0 (B4).
- **W9–11 — Evaluation (Component 6):** run B0–B4 + ablation; human eval with
  native raters; metric–human correlation.
- **W11–12 — Package:** freeze benchmark (D1), publish lexicon (D2), ship pipeline
  + README (D3), write up parity-vs-baseline result.

---

## 5. Success criteria (restated, measurable)
1. **Faithfulness:** 0 unsupported numeric claims on held-out reports (Component 5).
2. **Parity:** B4 ≥ B0 on faithfulness + register at comparable/lower token cost.
3. **Tokenization win:** documented fertility reduction vs standard BPE (Component 2).
4. **Reusability:** benchmark (D1) + lexicon (D2) usable by third parties.

---

## 6. Immediate next actions
1. **Decide the pilot domain** (Gram Panchayat activity report recommended).
2. Collect 3–10 real templates + matching source tables for it.
3. Confirm native-Marathi reviewers are available for evaluation.
4. Then I scaffold the repo: `data/`, `schemas/`, `lexicon/`, `pipeline/`, `eval/`.

---

## Reference index (by pillar)
- **Tokenization/morphology:** 2504.10335, 2607.23319, 2607.24276, 2506.17789, 2608.26449, 2608.18062, 2504.16977
- **Indic LLMs / benchmarks / data:** 2404.16816, 2507.13390, 2506.01615, 2602.22125, 2512.01852, 2606.24825, 2508.17444, 2605.27050, 2604.18423, 2607.23344, 2502.02100, 2606.30790
- **Data-to-text / faithfulness:** 2004.14373, 2505.23174, 2207.00397, 2312.02748, 2604.26501, 2207.12571, 2408.10490, 2311.09188, 2502.13674, 2410.12222
- **Evaluation beyond BLEU:** 2602.17425, 2509.17667, 2607.02235, 2501.12011
