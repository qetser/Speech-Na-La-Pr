"""Component 5: faithfulness / verification layer.

Guarantee: every numeric/entity claim in the report binds to a source cell.
Two checks:
  (a) sourced tokens must reference a real source_cell_id, and
  (b) NO unsourced token may contain a number (Latin 0-9 or Devanagari ०-९) --
      a stray digit means the generator wrote a figure outside the placeholder
      contract, i.e. a potential hallucination. We flag it.
"""
from __future__ import annotations

import re

from .parse import Record

# any run of Latin or Devanagari digits
_DIGIT_RUN = re.compile(r"[0-9०-९][0-9०-९,.०-९]*")

_DEV_TO_LATIN = str.maketrans("०१२३४५६७८९", "0123456789")


def _numbers_in(text: str) -> list[int]:
    """Extract canonical integer values from text (handles Devanagari digits,
    ₹, and Indian comma grouping like 25,00,000)."""
    out: list[int] = []
    for run in _DIGIT_RUN.findall(text.translate(_DEV_TO_LATIN)):
        digits = re.sub(r"[^0-9]", "", run)
        if digits:
            out.append(int(digits))
    return out


def freetext_tokens(text: str, record: Record) -> list[dict]:
    """Split free text into display tokens, marking each number as grounded
    (valid: it appears in the source) or fabricated (valid: False). Used to show
    the ungrounded baseline with its hallucinated figures flagged in red."""
    source_nums = set()
    for cell in record.values():
        source_nums.update(_numbers_in(cell.value))
    tokens: list[dict] = []
    pos = 0
    for m in _DIGIT_RUN.finditer(text):
        if m.start() > pos:
            tokens.append({"text": text[pos:m.start()]})
        run = m.group(0)
        digits = re.sub(r"[^0-9]", "", run.translate(_DEV_TO_LATIN))
        valid = bool(digits) and int(digits) in source_nums
        tokens.append({"text": run, "number": True, "valid": valid})
        pos = m.end()
    if pos < len(text):
        tokens.append({"text": text[pos:]})
    return tokens


def verify_freetext(text: str, record: Record) -> dict:
    """Faithfulness check for UNGROUNDED free text (the B1 baseline): every number
    in the report must appear in the source data, else it is a hallucination.
    Returns the same shape as verify() so the eval harness is engine-agnostic."""
    source_nums = set()
    for cell in record.values():
        source_nums.update(_numbers_in(cell.value))

    claims, unsupported = [], []
    for n in _numbers_in(text):
        valid = n in source_nums
        claims.append({"field": "number", "value": str(n),
                       "cell": "matched" if valid else "", "valid": valid})
        if not valid:
            unsupported.append({"reason": "fabricated_number", "text": str(n)})

    total = len(claims)
    traceable = sum(1 for c in claims if c["valid"])
    return {
        "ok": len(unsupported) == 0,
        "total": total,
        "traceable": traceable,
        "unsupported": len(unsupported),
        "unsupported_detail": unsupported,
        "claims": claims,
    }


def verify(slots: list[dict], record: Record) -> dict:
    valid_cells = {c.cell for c in record.values()}
    claims: list[dict] = []
    unsupported: list[dict] = []

    for slot in slots:
        for tok in slot["tokens"]:
            src = tok.get("source")
            if src:
                ok = src in valid_cells
                claims.append({
                    "field": tok.get("field", "?"),
                    "value": tok["text"],
                    "cell": src,
                    "valid": ok,
                })
                if not ok:
                    unsupported.append({"reason": "unknown_cell", "text": tok["text"], "cell": src})
            else:
                # unsourced text must not contain a bare number
                if _DIGIT_RUN.search(tok["text"]):
                    unsupported.append({
                        "reason": "ungrounded_number",
                        "text": tok["text"].strip(),
                        "slot": slot["id"],
                    })

    total = len(claims) + len([u for u in unsupported if u["reason"] == "ungrounded_number"])
    traceable = len([c for c in claims if c["valid"]])
    n_unsupported = len(unsupported)
    return {
        "ok": n_unsupported == 0,
        "total": total,
        "traceable": traceable,
        "unsupported": n_unsupported,
        "unsupported_detail": unsupported,
        "claims": claims,
    }
