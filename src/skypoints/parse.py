"""Read the pipe-delimited member file and the partner JSON feed.

Member file columns are found by HEADER NAME, never by position, so a missing or reordered
column (the spec lists Post Code, the sample file does not) cannot silently shift data.
"""
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .config import ALL_COLUMNS, REQUIRED_COLUMNS


class PipelineError(Exception):
    """A problem that must stop the run (bad header, unreadable file)."""


@dataclass
class Reject:
    row_ref: str
    reason: str
    detail: str


def file_date_from_name(path) -> date:
    """File name spec: SKYPOINTS_MEMBERS_YYYYMMDD.txt and SKYPOINTS_REDEMPTIONS_YYYYMMDD.json"""
    m = re.search(r"_(\d{8})\.[A-Za-z]+$", Path(path).name)
    if not m:
        raise PipelineError(f"File name must end with _YYYYMMDD.<ext>: {Path(path).name}")
    return datetime.strptime(m.group(1), "%Y%m%d").date()


def parse_member_file(path):
    """Return (rows, rejects, header_columns). Each row is a dict with row_num and the raw text fields."""
    # The design document shows records with a leading pipe (|H|..., |D|...); accept both styles.
    lines = [ln[1:] if ln.startswith("|") else ln for ln in Path(path).read_text(encoding="utf-8").splitlines()]
    if not lines or not lines[0].startswith("H|"):
        raise PipelineError("First line must be a header record starting with 'H|'")
    header = lines[0].split("|")[1:]
    by_lower = {h.strip().lower(): h.strip() for h in header}
    missing = [c for c in REQUIRED_COLUMNS if c.lower() not in by_lower]
    if missing:
        raise PipelineError(f"Header is missing mandatory columns: {missing}")
    rows, rejects = [], []
    for row_num, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        parts = line.split("|")
        if parts[0] != "D":
            rejects.append(Reject(str(row_num), "unknown_record_type", line[:200]))
            continue
        values = parts[1:]
        if len(values) != len(header):
            rejects.append(Reject(str(row_num), "column_count_mismatch",
                                  f"expected {len(header)} fields, got {len(values)}: {line[:200]}"))
            continue
        record = {h.strip().lower(): v for h, v in zip(header, values)}
        row = {"row_num": row_num}
        for col in ALL_COLUMNS:
            row[col.lower()] = record.get(col.lower())      # None when the column is absent from the header
        rows.append(row)
    return rows, rejects, [h.strip() for h in header]


def parse_redemption_file(path):
    """Return the list of JSON documents. Accepts one object, a list of objects, or JSON lines."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        data = json.loads(text)
        docs = data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        docs = [json.loads(ln) for ln in text.splitlines() if ln.strip()]
    return docs
