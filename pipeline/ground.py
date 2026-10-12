"""Component 3: content selection + retrieval grounding.

For each template slot, bind the exact source cells it is allowed to use. The
generator (Component 4) may ONLY reference these bound cells, so it can never
invent a figure. This is the plan-based grounding step (see plan.md, 2408.10490).
"""
from __future__ import annotations

from dataclasses import dataclass

from .parse import Cell, Record
from .schema import Schema


@dataclass
class BoundSlot:
    id: str
    intent: str
    evidence: dict[str, Cell]  # field_name -> Cell (value + source_cell_id)


def ground(record: Record, schema: Schema) -> list[BoundSlot]:
    bound: list[BoundSlot] = []
    for slot in schema.slots:
        evidence = {f: record[f] for f in slot.uses if f in record}
        missing = [f for f in slot.uses if f not in record]
        if missing:
            raise ValueError(f"Slot '{slot.id}' needs missing columns: {missing}")
        bound.append(BoundSlot(id=slot.id, intent=slot.intent, evidence=evidence))
    return bound
