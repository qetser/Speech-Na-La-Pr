"""Component 1: parse CSV into typed records with stable source_cell_ids.

Each cell gets a stable id `R{row}C{col}` (1-indexed). The verifier (Component 5)
checks every numeric/entity claim in the output against these ids. This is the
grounding contract: a value with no source_cell_id cannot appear in the report.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass


@dataclass
class Cell:
    value: str
    cell: str  # source_cell_id, e.g. "R1C5"

    def __str__(self) -> str:  # so f-strings print the value
        return self.value


Record = dict[str, Cell]


def parse_csv(csv_text: str, row_index: int = 1) -> Record:
    """Parse the header + one data row into a typed Record.

    row_index selects which data row (1-indexed) becomes the report subject.
    """
    reader = list(csv.reader(io.StringIO(csv_text.strip())))
    if len(reader) < 2:
        raise ValueError("CSV needs a header row and at least one data row.")
    headers = [h.strip() for h in reader[0]]
    if row_index >= len(reader):
        raise ValueError(f"Row {row_index} not found (CSV has {len(reader) - 1} data rows).")
    values = [v.strip() for v in reader[row_index]]
    if len(values) != len(headers):
        raise ValueError("Row/column count mismatch.")
    record: Record = {}
    for col, (h, v) in enumerate(zip(headers, values), start=1):
        record[h] = Cell(value=v, cell=f"R{row_index}C{col}")
    return record
