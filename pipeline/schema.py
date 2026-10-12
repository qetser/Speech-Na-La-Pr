"""Component 1 support: load a template spec S and the domain lexicon."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Slot:
    id: str
    intent: str
    uses: list[str] = field(default_factory=list)


@dataclass
class Schema:
    domain: str
    language: str
    register: str
    source_fields: list[dict[str, Any]]
    slots: list[Slot]
    verification: dict[str, Any]

    @property
    def field_names(self) -> list[str]:
        return [f["name"] for f in self.source_fields]


def load_schema(path: str | Path) -> Schema:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    slots = [Slot(id=s["id"], intent=s.get("intent", ""), uses=s.get("uses", []))
             for s in data["slots"]]
    return Schema(
        domain=data["domain"],
        language=data.get("language", "mr"),
        register=data.get("register", "administrative_formal"),
        source_fields=data["source_fields"],
        slots=slots,
        verification=data.get("verification", {}),
    )


def load_lexicon(path: str | Path) -> list[dict[str, str]]:
    """Load the terminology bank (Deliverable D2) as a list of rows."""
    text = Path(path).read_text(encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))
