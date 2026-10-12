"""Component 4: structure-constrained generation.

Key design (symbolic references, plan.md 2311.09188): the generator never writes
a raw number. It writes Marathi prose with {{field}} placeholders; we then resolve
each placeholder to its bound value + source_cell_id. This makes every data value
traceable BY CONSTRUCTION, and the verifier (Component 5) catches any stray digit
the model wrote outside a placeholder.

Two engines, same output contract:
  - "deterministic": fixed register-controlled Marathi scaffolding (offline, always works)
  - "llm": an Indic-capable LLM (OpenAI GPT) fills the same placeholder contract
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from .ground import BoundSlot
from .schema import Schema

PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")

# Deterministic Marathi scaffolding for the Gram Panchayat domain.
_DET_TEMPLATES_MR: dict[str, str] = {
    "header": "{{gp_name}}, {{taluka}} तालुका, {{district}} जिल्हा, कार्य अहवाल ({{period}}).",
    "coverage": "या कालावधीत एकूण {{households}} कुटुंबांचा समावेश करण्यात आला.",
    "works": "अहवाल कालावधीत {{works_done}} कामे पूर्ण करण्यात आली.",
    "finance": "प्राप्त निधी {{funds_received}} पैकी {{funds_spent}} खर्च करण्यात आला.",
    "beneficiaries": "एकूण {{beneficiaries}} लाभार्थ्यांपर्यंत लाभ पोहोचला.",
}


def _money_fields(schema: Schema) -> set[str]:
    return {f["name"] for f in schema.source_fields if f.get("type") == "money"}


def _format_value(field: str, cell_value: str, money: set[str]) -> str:
    if field in money:
        try:
            return "₹" + format(int(float(cell_value)), ",d")
        except ValueError:
            return cell_value
    return cell_value


def _resolve(text: str, evidence: dict, money: set[str]) -> list[dict[str, Any]]:
    """Split a placeholder-bearing string into tokens, binding each {{field}}."""
    tokens: list[dict[str, Any]] = []
    pos = 0
    for m in PLACEHOLDER.finditer(text):
        if m.start() > pos:
            tokens.append({"text": text[pos:m.start()]})
        field = m.group(1)
        cell = evidence.get(field)
        if cell is None:
            # Placeholder referencing an unbound field -> leave visible, no source.
            tokens.append({"text": m.group(0)})
        else:
            tokens.append({
                "text": _format_value(field, cell.value, money),
                "source": cell.cell,
                "field": field,
            })
        pos = m.end()
    if pos < len(text):
        tokens.append({"text": text[pos:]})
    return tokens


def generate_deterministic(bound: list[BoundSlot], schema: Schema) -> list[dict]:
    money = _money_fields(schema)
    slots = []
    for bs in bound:
        template = _DET_TEMPLATES_MR.get(bs.id)
        if template is None:
            # generic fallback for unknown slots: "field: {{field}}" list
            template = "; ".join(f"{f}: {{{{{f}}}}}" for f in bs.evidence) + "."
        slots.append({"id": bs.id, "tokens": _resolve(template, bs.evidence, money)})
    return slots


# --------------------------- LLM engine ---------------------------
# Uses OpenAI (GPT) when OPENAI_API_KEY is set. Model is OPENAI_MODEL (default gpt-4o).

def llm_available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _llm_complete(prompt: str, max_tokens: int = 1500) -> str:
    """Return raw model text for a single user prompt."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("No LLM key set (OPENAI_API_KEY).")
    from openai import OpenAI
    client = OpenAI()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    resp = client.chat.completions.create(
        model=model, max_tokens=max_tokens, temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


def _build_prompt(bound: list[BoundSlot], schema: Schema, lexicon: list[dict]) -> str:
    lex_lines = [
        f"- {r['english']} -> {r['marathi_formal']} (register: {r.get('register','')})"
        for r in lexicon if r.get("marathi_formal")
    ]
    slot_lines = []
    for bs in bound:
        ev = ", ".join(f"{{{{{f}}}}}={c.value}" for f, c in bs.evidence.items())
        slot_lines.append(f'  - id "{bs.id}": {bs.intent}\n    available values: {ev}')
    return f"""You are generating a {schema.register} report in Marathi (Devanagari).

HARD RULES:
1. Write every data value ONLY as its {{{{placeholder}}}} token, never the raw number
   or name. Example: write "{{{{households}}}} कुटुंबे", never "1240 कुटुंबे".
2. Use ONLY the placeholders listed for each slot. Do not invent values.
3. Keep the administrative Marathi register. Avoid English/code-mixing.

Terminology (use these forms):
{chr(10).join(lex_lines)}

Produce one short Marathi sentence per slot, in order:
{chr(10).join(slot_lines)}

Return ONLY JSON: {{"slots": [{{"id": "...", "text": "... {{{{field}}}} ..."}}, ...]}}"""


def generate_llm(bound: list[BoundSlot], schema: Schema, lexicon: list[dict]) -> list[dict]:
    """Grounded LLM generation (the B4 system): the model writes Marathi using
    {{placeholder}} tokens only, so every value is traceable by construction."""
    prompt = _build_prompt(bound, schema, lexicon)
    raw = _llm_complete(prompt)
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    data = json.loads(raw)

    money = _money_fields(schema)
    ev_by_id = {bs.id: bs.evidence for bs in bound}
    slots = []
    for item in data["slots"]:
        evidence = ev_by_id.get(item["id"], {})
        slots.append({"id": item["id"], "tokens": _resolve(item["text"], evidence, money)})
    return slots


def generate_llm_ungrounded(bound: list[BoundSlot], schema: Schema,
                            lexicon: list[dict]) -> str:
    """UNGROUNDED LLM generation (the B1 baseline): the model writes a natural
    Marathi report from the raw values, with NO placeholder constraint and NO
    verifier. This is the control that exposes the hallucination problem the
    grounded system (B4) fixes. Returns plain text."""
    lex_lines = [f"- {r['english']} -> {r['marathi_formal']}"
                 for r in lexicon if r.get("marathi_formal")]
    rows = []
    for bs in bound:
        for f, c in bs.evidence.items():
            rows.append(f"{f} = {c.value}")
    prompt = f"""Write a short {schema.register} report in Marathi (Devanagari) for a
Gram Panchayat, based on the data below. Write naturally and completely.

Data:
{chr(10).join(dict.fromkeys(rows))}

Preferred terminology:
{chr(10).join(lex_lines)}

Return only the Marathi report text."""
    return _llm_complete(prompt).strip()


def generate(bound: list[BoundSlot], schema: Schema, lexicon: list[dict],
             engine: str = "auto") -> tuple[list[dict], str]:
    """Return (slots, engine_used). 'auto' uses the LLM iff an API key is set."""
    use_llm = (engine == "llm") or (engine == "auto" and llm_available())
    if use_llm:
        if not llm_available():
            raise RuntimeError("engine='llm' requires OPENAI_API_KEY.")
        try:
            return generate_llm(bound, schema, lexicon), "llm"
        except Exception as e:  # never let the demo break; fall back
            if engine == "llm":
                raise
            print(f"[generate] LLM failed ({e}); falling back to deterministic.")
    return generate_deterministic(bound, schema), "deterministic"
