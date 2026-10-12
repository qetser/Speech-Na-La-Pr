"""Free-form grounded report generation + LaTeX rendering.

Flow: the user gives a SUBJECT and a set of DETAILS (label/value facts, plus
optional free-text notes). The system writes a full multi-section Marathi report,
keeping every fact value grounded via {{slug}} placeholders, verifies it, and
renders a compile-ready XeLaTeX document.

Public: build_report(subject, facts, report_type, notes, engine) -> dict
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from datetime import date
from pathlib import Path

from .generate import PLACEHOLDER, _llm_complete, _resolve, llm_available
from .parse import Cell
from .train_tokenizer import OUT as BPE_PATH
from .verify import freetext_tokens, verify, verify_freetext

TEMPLATE = Path(__file__).resolve().parent.parent / "latex" / "template.tex"

_OUR_TOK = None
_GPT_ENC = None


def _report_text(title: str, sections: list[dict]) -> str:
    parts = [title]
    for s in sections:
        parts.append(s["heading"])
        parts.append("".join(t["text"] for t in s["tokens"]))
    return "\n".join(parts)


def _token_metrics(text: str) -> dict:
    """Compare our trained Marathi tokenizer vs GPT-4o's on the generated report:
    token counts, encode time, and fertility (tokens/word)."""
    global _OUR_TOK, _GPT_ENC
    words = max(len(text.split()), 1)
    out: dict = {"report_words": words, "our": None, "gpt": None, "token_saving_x": None}
    try:
        from tokenizers import Tokenizer
        if _OUR_TOK is None and BPE_PATH.exists():
            _OUR_TOK = Tokenizer.from_file(str(BPE_PATH))
        if _OUR_TOK is not None:
            t0 = time.perf_counter()
            n = len(_OUR_TOK.encode(text).tokens)
            out["our"] = {"tokens": n, "ms": round((time.perf_counter() - t0) * 1000, 2),
                          "fertility": round(n / words, 3)}
    except Exception:
        pass
    try:
        import tiktoken
        if _GPT_ENC is None:
            _GPT_ENC = tiktoken.get_encoding("o200k_base")
        t0 = time.perf_counter()
        n = len(_GPT_ENC.encode(text))
        out["gpt"] = {"tokens": n, "ms": round((time.perf_counter() - t0) * 1000, 2),
                      "fertility": round(n / words, 3)}
    except Exception:
        pass
    if out["our"] and out["gpt"] and out["our"]["tokens"]:
        out["token_saving_x"] = round(out["gpt"]["tokens"] / out["our"]["tokens"], 2)
    return out


def slugify(label: str, i: int) -> str:
    s = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s or f"fact{i}"


def _record_from_facts(facts: list[dict]) -> dict[str, Cell]:
    """facts = [{label, value}] -> {slug: Cell(value, 'F{i}')}."""
    record: dict[str, Cell] = {}
    for i, f in enumerate(facts, start=1):
        label = str(f.get("label", "")).strip()
        value = str(f.get("value", "")).strip()
        if not value:
            continue
        slug = slugify(label, i)
        base, n = slug, 2
        while slug in record:          # ensure uniqueness
            slug = f"{base}_{n}"; n += 1
        record[slug] = Cell(value=value, cell=f"F{i}")
        record[slug].label = label     # type: ignore[attr-defined]
    return record


# --------------------------- generation ---------------------------

def _prompt(subject: str, report_type: str, record: dict, notes: str) -> str:
    facts = "\n".join(
        f"  - {{{{{slug}}}}} = {c.value}   (label: {getattr(c, 'label', slug)})"
        for slug, c in record.items()
    )
    note_block = f"\nBackground context (do NOT invent numbers from this):\n{notes}\n" if notes else ""
    return f"""You are an administrative report writer. Write a {report_type or 'formal'} report
in Marathi (Devanagari), in a formal administrative register, about:

SUBJECT: {subject}

HARD RULES:
1. Every data value MUST be written ONLY as its {{{{placeholder}}}} token, never the
   raw number or name. Example: write "{{{{households}}}} कुटुंबे", not "1240 कुटुंबे".
2. Use ONLY the placeholders listed below. Never introduce a number that is not a
   placeholder.
3. Formal Marathi register; avoid English / code-mixing.

Available facts:
{facts}
{note_block}
Organise the report into 2-5 titled sections. Return ONLY JSON:
{{"title": "<Marathi title>",
  "sections": [{{"heading": "<Marathi heading>", "body": "<Marathi text with {{{{placeholders}}}}>"}}]}}"""


def _deterministic(subject: str, report_type: str, record: dict, notes: str) -> dict:
    """Offline fallback: a titled report listing the facts. Guarantees grounding."""
    body = "या अहवालात खालील तपशील नमूद करण्यात आले आहेत: " + ", ".join(
        f"{getattr(c, 'label', slug)} {{{{{slug}}}}}" for slug, c in record.items()
    ) + "."
    return {"title": subject or "अहवाल",
            "sections": [{"heading": "तपशील", "body": body}]}


def build_report(subject: str, facts: list[dict], report_type: str = "",
                 notes: str = "", engine: str = "auto") -> dict:
    t_start = time.perf_counter()
    record = _record_from_facts(facts)
    use_llm = (engine == "llm") or (engine == "auto" and llm_available())

    data, engine_used, llm_ms = None, "deterministic", 0.0
    if use_llm:
        try:
            t0 = time.perf_counter()
            raw = _llm_complete(_prompt(subject, report_type, record, notes))
            llm_ms = round((time.perf_counter() - t0) * 1000, 1)
            raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
            data, engine_used = json.loads(raw), "llm"
        except Exception as e:
            if engine == "llm":
                raise
            print(f"[report] LLM failed ({e}); using deterministic.")
    if data is None:
        data = _deterministic(subject, report_type, record, notes)

    # Resolve placeholders in each section into grounded tokens.
    sections = []
    for s in data.get("sections", []):
        tokens = _resolve(s.get("body", ""), record, set())
        sections.append({"heading": s.get("heading", ""), "tokens": tokens})

    verification = verify([{"id": s["heading"], "tokens": s["tokens"]} for s in sections], record)
    title = data.get("title") or subject or "अहवाल"
    latex = to_latex(title, sections)

    metrics = {
        "llm_ms": llm_ms,
        "total_ms": round((time.perf_counter() - t_start) * 1000, 1),
        "tokenization": _token_metrics(_report_text(title, sections)),
    }
    return {"title": title, "sections": sections, "verification": verification,
            "latex": latex, "engine": engine_used, "metrics": metrics}


# ----------------- ungrounded baseline (B1) + comparison -----------------

def _ungrounded_prompt(subject: str, report_type: str, record: dict, notes: str) -> str:
    # A realistic, unconstrained request: people ask LLMs for detailed, analytical
    # reports. That is exactly where free-form generation pads with figures that
    # were never in the data -- the hallucination this project prevents.
    facts = "\n".join(f"  - {getattr(c, 'label', slug)}: {c.value}"
                      for slug, c in record.items())
    note_block = f"\nBackground: {notes}\n" if notes else ""
    return f"""Write a detailed, comprehensive {report_type or 'formal'} report in Marathi
(Devanagari), formal administrative register, about: {subject}

Base it on the information below, but make it thorough: add relevant context,
analysis, progress indicators and supporting statistics so it reads like a
complete official report.
{facts}{note_block}
Return only the Marathi report text."""


def generate_ungrounded(subject: str, facts: list[dict], report_type: str = "",
                        notes: str = "") -> str:
    record = _record_from_facts(facts)
    return _llm_complete(_ungrounded_prompt(subject, report_type, record, notes)).strip()


def build_comparison(subject: str, facts: list[dict], report_type: str = "",
                     notes: str = "", engine: str = "auto") -> dict:
    """Produce BOTH results for side-by-side teaching:
      - grounded (B4, our system): every figure bound + verified
      - ungrounded (B1, plain LLM): free-form, numbers checked against source
    """
    grounded = build_report(subject, facts, report_type, notes, engine)

    ungrounded = None
    if llm_available() and engine != "deterministic":
        try:
            record = _record_from_facts(facts)
            text = generate_ungrounded(subject, facts, report_type, notes)
            ungrounded = {
                "tokens": freetext_tokens(text, record),
                "verification": verify_freetext(text, record),
            }
        except Exception as e:
            print(f"[compare] ungrounded failed ({e}).")

    return {"subject": subject, "grounded": grounded, "ungrounded": ungrounded,
            "metrics": grounded["metrics"], "engine": grounded["engine"]}


# --------------------------- LaTeX rendering ---------------------------

_LATEX_ESCAPE = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
    "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}", "₹": r"रु.\,",
}


def _esc(text: str) -> str:
    return "".join(_LATEX_ESCAPE.get(ch, ch) for ch in text)


def to_latex(title: str, sections: list[dict]) -> str:
    body_parts = []
    for s in sections:
        body_parts.append(f"\\section*{{{_esc(s['heading'])}}}")
        line = []
        for t in s["tokens"]:
            if t.get("source"):              # grounded value -> bold (traceable)
                line.append(f"\\textbf{{{_esc(t['text'])}}}")
            else:
                line.append(_esc(t["text"]))
        body_parts.append("".join(line))
    body = "\n\n".join(body_parts)
    tpl = TEMPLATE.read_text(encoding="utf-8")
    return (tpl.replace("%%TITLE%%", _esc(title))
               .replace("%%DATE%%", date.today().isoformat())
               .replace("%%BODY%%", body))
