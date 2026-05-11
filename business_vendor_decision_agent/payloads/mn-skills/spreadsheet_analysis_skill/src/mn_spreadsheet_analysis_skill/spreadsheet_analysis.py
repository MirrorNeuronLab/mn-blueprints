from __future__ import annotations

import csv
import math
import re
from collections import Counter
from datetime import datetime
from io import StringIO
from statistics import mean, median
from typing import Any


MISSING_VALUES = {"", "na", "n/a", "none", "null", "-"}


def read_csv_table(text: str) -> list[dict[str, str]]:
    """Read CSV text into a list of row dictionaries."""

    reader = csv.DictReader(StringIO(text))
    return [dict(row) for row in reader]


def profile_table(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Profile rows from a spreadsheet-like table."""

    columns = _column_names(rows)
    column_profiles = {column: _profile_column(column, [row.get(column) for row in rows]) for column in columns}
    return {
        "row_count": len(rows),
        "column_count": len(columns),
        "columns": column_profiles,
        "quality_flags": _quality_flags(rows, column_profiles),
    }


def detect_column_type(values: list[Any]) -> str:
    """Classify a column as numeric, date, boolean, or text."""

    present = [_coerce_text(value) for value in values if not _is_missing(value)]
    if not present:
        return "empty"
    if all(_parse_float(value) is not None for value in present):
        return "numeric"
    if all(_parse_bool(value) is not None for value in present):
        return "boolean"
    if all(_parse_date(value) is not None for value in present):
        return "date"
    return "text"


def summarize_table_profile(profile: dict[str, Any]) -> list[str]:
    """Return short human-readable observations from a table profile."""

    observations = [
        f"{profile.get('row_count', 0)} rows across {profile.get('column_count', 0)} columns."
    ]
    for name, column in profile.get("columns", {}).items():
        if column["type"] == "numeric":
            observations.append(
                f"{name}: average {column['mean']}, median {column['median']}, range {column['min']} to {column['max']}."
            )
        if column["missing_count"]:
            observations.append(f"{name}: {column['missing_count']} missing value(s).")
    observations.extend(profile.get("quality_flags", []))
    return observations


def _profile_column(name: str, values: list[Any]) -> dict[str, Any]:
    column_type = detect_column_type(values)
    present = [_coerce_text(value) for value in values if not _is_missing(value)]
    profile: dict[str, Any] = {
        "name": name,
        "type": column_type,
        "count": len(values),
        "present_count": len(present),
        "missing_count": len(values) - len(present),
        "unique_count": len(set(present)),
    }

    if column_type == "numeric":
        numbers = [_parse_float(value) for value in present]
        numeric_values = [number for number in numbers if number is not None]
        profile.update(
            {
                "min": _round_number(min(numeric_values)),
                "max": _round_number(max(numeric_values)),
                "mean": _round_number(mean(numeric_values)),
                "median": _round_number(median(numeric_values)),
            }
        )
    elif column_type == "text":
        common = Counter(present).most_common(5)
        profile["top_values"] = [{"value": value, "count": count} for value, count in common]
    return profile


def _quality_flags(rows: list[dict[str, Any]], columns: dict[str, dict[str, Any]]) -> list[str]:
    flags: list[str] = []
    if not rows:
        flags.append("Table has no rows.")
    for name, profile in columns.items():
        if rows and profile["missing_count"] == len(rows):
            flags.append(f"{name} is entirely empty.")
        elif profile["missing_count"]:
            flags.append(f"{name} has missing values.")
    return flags


def _column_names(rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for name in row:
            if name not in seen:
                names.append(name)
                seen.add(name)
    return names


def _parse_float(value: str) -> float | None:
    value = _coerce_text(value).replace(",", "")
    if not value:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _parse_bool(value: str) -> bool | None:
    normalized = _coerce_text(value).lower()
    if normalized in {"true", "yes", "y", "1"}:
        return True
    if normalized in {"false", "no", "n", "0"}:
        return False
    return None


def _parse_date(value: str) -> datetime | None:
    value = _coerce_text(value)
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, pattern)
        except ValueError:
            continue
    return None


def _is_missing(value: Any) -> bool:
    return _coerce_text(value).lower() in MISSING_VALUES


def _coerce_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _round_number(value: float) -> int | float:
    rounded = round(value, 4)
    return int(rounded) if rounded.is_integer() else rounded
