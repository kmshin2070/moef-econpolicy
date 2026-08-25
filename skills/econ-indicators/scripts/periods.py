"""Pure functions for period-label handling: formatting a date/parts into
this project's period label convention, and sliding-window retention.

No network access and no env var reads anywhere in this module -- it is
unit tested directly (see tests/test_periods.py).
"""

from __future__ import annotations

import datetime as _dt


def _resolve_year_month(date_or_parts):
    """Internal: normalize the many acceptable input shapes for
    format_period down to (year, month_or_None)."""
    if isinstance(date_or_parts, (_dt.date, _dt.datetime)):
        return date_or_parts.year, date_or_parts.month
    if isinstance(date_or_parts, tuple):
        if len(date_or_parts) == 1:
            return date_or_parts[0], None
        return date_or_parts[0], date_or_parts[1]
    if isinstance(date_or_parts, int):
        return date_or_parts, None
    if isinstance(date_or_parts, str):
        s = date_or_parts.strip()
        if "Q" in s.upper() and "-" not in s:
            year_part, q_part = s.upper().split("Q")
            year = int(year_part)
            quarter = int(q_part)
            return year, quarter * 3  # any month within that quarter works
        if "-" in s:
            parts = s.split("-")
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else None
            return year, month
        return int(s), None
    raise TypeError(f"format_period: unsupported input type {type(date_or_parts)!r}")


def format_period(date_or_parts, frequency: str) -> str:
    """Format a date/parts into this project's period label convention:
    monthly -> "YYYY-MM", quarterly -> "YYYYQn", annual -> "YYYY".

    `date_or_parts` accepts: a datetime.date/datetime, a (year, month)
    tuple, a bare int/1-tuple year (annual only), or a string already in
    "YYYY-MM-DD" / "YYYY-MM" / "YYYYQn" / "YYYY" form.
    """
    year, month = _resolve_year_month(date_or_parts)
    if frequency == "monthly":
        if month is None:
            raise ValueError("format_period: monthly requires a month")
        return f"{year:04d}-{month:02d}"
    if frequency == "quarterly":
        if month is None:
            raise ValueError("format_period: quarterly requires a month/quarter")
        quarter = (month - 1) // 3 + 1
        return f"{year:04d}Q{quarter}"
    if frequency == "annual":
        return f"{year:04d}"
    raise ValueError(f"format_period: unknown frequency {frequency!r}")


def _period_sort_key(period: str, frequency: str):
    if frequency == "monthly":
        year, month = period.split("-")
        return (int(year), int(month))
    if frequency == "quarterly":
        year_part, q_part = period.upper().split("Q")
        return (int(year_part), int(q_part))
    if frequency == "annual":
        return (int(period),)
    raise ValueError(f"_period_sort_key: unknown frequency {frequency!r}")


def sliding_window(
    all_periods: list[str], frequency: str, retain_periods_by_frequency: dict
) -> tuple:
    """Sort `all_periods` chronologically (per `frequency`'s label format)
    and keep the most recent retain_periods_by_frequency[frequency] of
    them. Returns (kept, dropped), both chronologically sorted ascending.
    Duplicate labels in the input are de-duplicated."""
    retain_n = retain_periods_by_frequency[frequency]
    unique_periods = sorted(set(all_periods), key=lambda p: _period_sort_key(p, frequency))
    if retain_n <= 0:
        return [], unique_periods
    kept = unique_periods[-retain_n:]
    dropped = unique_periods[: len(unique_periods) - len(kept)]
    return kept, dropped
