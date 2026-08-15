#!/usr/bin/env python3
"""Measure whether a structured record family carries information or ceremony.

The review layer diagnoses `信息密度均匀`: every beat carrying nearly the same
amount of new information, so nothing reads as an event. A fixed-field record
template can produce that shape by construction — every shot gets the same
twenty fields whether it deserves them or not — but that is a hypothesis, not
a finding, and it has to be measured on real episodes rather than argued.

This reports two things per JSONL family:

* **CV** — the coefficient of variation of per-record content volume. Near zero
  means every record is the same size, which is what a form produces. Prose
  that lets a throwaway shot be one line and a decisive shot be twenty does not
  look like that.
* **Ceremony fields** — fields whose value is identical in every record, or
  which are empty in every record. Those carry no per-record information: they
  are the form asserting itself. They are the first candidates to drop.

It reads accepted creator files and writes nothing. It makes no judgement about
the drama; a low CV is a question worth asking, not a defect.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any


MINIMUM_PYTHON = (3, 10)
if sys.version_info < MINIMUM_PYTHON:
    raise SystemExit(
        "short-drama needs Python {}.{} or newer; this interpreter is {}.{}".format(
            *MINIMUM_PYTHON, sys.version_info.major, sys.version_info.minor
        )
    )

# Plumbing that is supposed to repeat: it identifies versions, it is not content.
PLUMBING = {"owner", "artifact", "hash", "authority", "field", "status", "provenance"}


def content_size(value: Any) -> int:
    """Size of the human-authored content, ignoring reference plumbing."""

    if isinstance(value, dict):
        return sum(
            content_size(item) for key, item in value.items() if key not in PLUMBING
        )
    if isinstance(value, list):
        return sum(content_size(item) for item in value)
    if isinstance(value, str):
        return len(value)
    return 0


def load_markdown_table(text: str) -> list[dict[str, Any]]:
    """Read the largest Markdown table as records, header cells as field names.

    A shot table is the same fixed form as a JSONL template wearing different
    punctuation, so the same question applies to it: are the columns carrying
    per-shot information, or is the row just being filled in?
    """

    tables: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            current.append(line.strip())
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    if not tables:
        return []

    rows = max(tables, key=len)

    def cells(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip("|").split("|")]

    header = cells(rows[0])
    records = []
    for line in rows[1:]:
        values = cells(line)
        # The |---|---| separator carries no data.
        if all(set(value) <= {"-", ":"} for value in values if value):
            continue
        records.append(
            {
                header[index] if index < len(header) else f"col{index}": value
                for index, value in enumerate(values)
            }
        )
    return records


def load(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".md", ".markdown"}:
        return load_markdown_table(text)
    records = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError(f"{path.name} line {number} is not a JSON object")
        records.append(record)
    return records


def measure(path: Path) -> dict[str, Any]:
    records = load(path)
    if len(records) < 3:
        return {"file": path.name, "records": len(records), "note": "too few records to measure"}

    sizes = [content_size(record) for record in records]
    mean = statistics.mean(sizes)
    cv = statistics.pstdev(sizes) / mean if mean else 0.0

    keys: set[str] = set()
    for record in records:
        keys |= set(record)
    constant: list[str] = []
    empty: list[str] = []
    for key in sorted(keys):
        values = [json.dumps(record.get(key), sort_keys=True, ensure_ascii=False) for record in records]
        if all(content_size(record.get(key)) == 0 for record in records):
            empty.append(key)
        elif len(set(values)) == 1:
            constant.append(key)

    # Exact equality misses the more common shape: a column that is not
    # literally constant but still says the same thing in most rows. Distinct
    # values per record is the readable version of that question.
    variety = {}
    for key in sorted(keys):
        values = [
            json.dumps(record.get(key), sort_keys=True, ensure_ascii=False)
            for record in records
            if content_size(record.get(key))
        ]
        if values:
            variety[key] = round(len(set(values)) / len(values), 2)
    low_variety = sorted(key for key, ratio in variety.items() if ratio <= 0.5)

    return {
        "file": path.name,
        "records": len(records),
        "field_variety": variety,
        "low_variety_fields": low_variety,
        "content_chars": {
            "min": min(sizes),
            "median": int(statistics.median(sizes)),
            "max": max(sizes),
            "cv": round(cv, 3),
            "max_over_min": round(max(sizes) / min(sizes), 1) if min(sizes) else None,
        },
        "ceremony": {
            "always_empty": empty,
            "identical_in_every_record": constant,
            "share_of_fields": round((len(empty) + len(constant)) / len(keys), 2) if keys else 0.0,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Measure per-record information density and ceremony fields."
    )
    parser.add_argument(
        "paths", type=Path, nargs="+",
        help="JSONL or Markdown-table files, or a directory to scan",
    )
    args = parser.parse_args(argv)

    targets: list[Path] = []
    for path in args.paths:
        if path.is_dir():
            targets.extend(sorted(path.rglob("*.jsonl")) + sorted(path.rglob("*.md")))
        else:
            targets.append(path)

    results = []
    for target in targets:
        try:
            results.append(measure(target))
        except (OSError, ValueError, json.JSONDecodeError) as error:
            results.append({"file": str(target), "error": f"{type(error).__name__}: {error}"})
    print(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
