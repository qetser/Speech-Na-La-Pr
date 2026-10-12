"""The baseline ladder (plan.md section 3).

Each system maps a source CSV -> (rendered_text, verification). Comparing them on
the SAME benchmark isolates what each component contributes.

  - B2 (grounded + structured, deterministic) : always runs, no API needed.
  - B1 (ungrounded LLM, no verifier)          : runs with an LLM key. The CONTROL
        that exposes hallucination: the model writes freely, and we check every
        number against the source. Fabricated figures show up here.
  - B4 (grounded LLM + verifier, our system)  : runs with an LLM key. Numbers are
        bound to source cells by construction, so faithfulness is enforced.

B0 (English -> translate pivot) needs an MT backend; hook left in place below.
"""
from __future__ import annotations

from typing import Callable

from pipeline.generate import (generate_deterministic, generate_llm,
                               generate_llm_ungrounded, llm_available)
from pipeline.ground import ground
from pipeline.parse import parse_csv
from pipeline.run import DEFAULT_LEXICON, DEFAULT_SCHEMA
from pipeline.schema import load_lexicon, load_schema
from pipeline.verify import verify, verify_freetext

_SCHEMA = load_schema(DEFAULT_SCHEMA)
_LEXICON = load_lexicon(DEFAULT_LEXICON)


def _render(slots: list[dict]) -> str:
    return "\n".join("".join(t["text"] for t in s["tokens"]) for s in slots)


def _b2_deterministic(csv_text: str) -> tuple[str, dict]:
    record = parse_csv(csv_text)
    bound = ground(record, _SCHEMA)
    slots = generate_deterministic(bound, _SCHEMA)
    return _render(slots), verify(slots, record)


def _b1_ungrounded_llm(csv_text: str) -> tuple[str, dict]:
    record = parse_csv(csv_text)
    bound = ground(record, _SCHEMA)
    text = generate_llm_ungrounded(bound, _SCHEMA, _LEXICON)   # free-form, no placeholders
    return text, verify_freetext(text, record)                 # numbers checked vs source


def _b4_full_llm(csv_text: str) -> tuple[str, dict]:
    record = parse_csv(csv_text)
    bound = ground(record, _SCHEMA)
    slots = generate_llm(bound, _SCHEMA, _LEXICON)             # placeholder-constrained
    return _render(slots), verify(slots, record)


def available_systems() -> dict[str, Callable[[str], tuple[str, dict]]]:
    systems: dict[str, Callable] = {"B2_grounded_structured_det": _b2_deterministic}
    if llm_available():
        systems["B1_ungrounded_llm"] = _b1_ungrounded_llm
        systems["B4_grounded_llm"] = _b4_full_llm
    return systems
