"""Orchestrator: wire Components 1 -> 3 -> 4 -> 5 into one call."""
from __future__ import annotations

from pathlib import Path

from .generate import generate
from .ground import ground
from .parse import parse_csv
from .schema import Schema, load_lexicon, load_schema

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA = ROOT / "schemas" / "gram_panchayat_activity_report.yaml"
DEFAULT_LEXICON = ROOT / "lexicon" / "marathi_admin_lexicon.csv"


def run_pipeline(csv_text: str, schema: Schema | str | None = None,
                 lexicon: list | str | None = None, engine: str = "auto",
                 row_index: int = 1) -> dict:
    if schema is None:
        schema = load_schema(DEFAULT_SCHEMA)
    elif isinstance(schema, str):
        schema = load_schema(schema)
    if lexicon is None:
        lexicon = load_lexicon(DEFAULT_LEXICON)
    elif isinstance(lexicon, str):
        lexicon = load_lexicon(lexicon)

    record = parse_csv(csv_text, row_index=row_index)            # Component 1
    bound = ground(record, schema)                               # Component 3
    slots, engine_used = generate(bound, schema, lexicon, engine)  # Component 4
    from .verify import verify
    verification = verify(slots, record)                        # Component 5

    return {"slots": slots, "verification": verification, "engine": engine_used,
            "domain": schema.domain}
