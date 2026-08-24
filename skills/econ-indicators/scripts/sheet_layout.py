"""Pure functions for sheet layout math: tab grain resolution, period
label formatting, coarse-to-fine period mapping, spreadsheet column
letters, sliding-window retention, row diffing, and row assignment.

No network access and no env var reads anywhere in this module -- it is
unit tested directly (see tests/test_sheet_layout.py).
"""

from __future__ import annotations

import datetime as _dt

_FREQUENCY_PRECEDENCE = ("monthly", "quarterly", "annual")


def resolve_tab_grain(indicators_in_category: list[dict]) -> str:
    """Return the finest frequency present among `indicators_in_category`.
    Precedence: monthly > quarterly > annual (monthly is "finest")."""
    if not indicators_in_category:
        raise ValueError("resolve_tab_grain: indicators_in_category is empty")
    freqs = {ind["frequency"] for ind in indicators_in_category}
    for candidate in _FREQUENCY_PRECEDENCE:
        if candidate in freqs:
            return candidate
    raise ValueError(f"resolve_tab_grain: no recognized frequency in {freqs!r}")


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


def map_to_grain_column(period_label: str, from_frequency: str, to_grain: str) -> str:
    """Map a (possibly coarser) `period_label` at `from_frequency` onto
    the tab's `to_grain` column label. A coarser row maps to the *end*
    period of its span at the finer grain: quarter -> last month of the
    quarter ("2024Q1" + to_grain monthly -> "2024-03"); year -> December
    ("2024" + to_grain monthly -> "2024-12"). Same-frequency (or any
    combination not covered above) is returned unchanged (identity)."""
    if from_frequency == to_grain:
        return period_label

    if from_frequency == "quarterly" and to_grain == "monthly":
        year_part, q_part = period_label.upper().split("Q")
        year = int(year_part)
        quarter = int(q_part)
        month = quarter * 3
        return f"{year:04d}-{month:02d}"

    if from_frequency == "annual" and to_grain == "monthly":
        year = int(period_label)
        return f"{year:04d}-12"

    if from_frequency == "annual" and to_grain == "quarterly":
        year = int(period_label)
        return f"{year:04d}Q4"

    # Any other combination (including a finer frequency somehow landing
    # in a coarser tab, which should not happen given resolve_tab_grain's
    # precedence rules): identity, per spec.
    return period_label


def column_letter(index: int) -> str:
    """Standard base-26 spreadsheet column letters, 1-based:
    1 -> "A", 26 -> "Z", 27 -> "AA", 28 -> "AB", ..., 52 -> "AZ",
    53 -> "BA", ... Correct arbitrarily far beyond Z."""
    if index < 1:
        raise ValueError(f"column_letter: index must be >= 1, got {index}")
    letters = []
    n = index
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        letters.append(chr(ord("A") + remainder))
    return "".join(reversed(letters))


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


def diff_rows(current_state_row, fresh_periods: list[dict], tolerance: float = 1e-9) -> list[dict]:
    """Return the minimal list of {"period", "value"} entries from
    `fresh_periods` that are new (period not present in the current sheet
    state) or changed beyond `tolerance` compared to the current state.

    `current_state_row` is {"row": int, "values": {period: value}} or
    None (brand-new row -> every fresh period counts as new)."""
    existing_values = {}
    if current_state_row is not None:
        existing_values = current_state_row.get("values", {}) or {}

    changed = []
    for entry in fresh_periods:
        period = entry["period"]
        value = entry["value"]
        if period not in existing_values:
            changed.append({"period": period, "value": value})
            continue
        old_value = existing_values[period]
        if old_value is None or abs(float(old_value) - float(value)) > tolerance:
            changed.append({"period": period, "value": value})
    return changed


def assign_row(
    category_state: dict, indicator_id: str, existing_max_row: int, header_row: int
) -> int:
    """Reuse the existing row for `indicator_id` if `category_state`
    already has one recorded, else assign
    max(existing_max_row, header_row) + 1 (a brand-new row)."""
    rows = (category_state or {}).get("rows", {}) or {}
    existing = rows.get(indicator_id)
    if existing is not None:
        return existing["row"]
    return max(existing_max_row, header_row) + 1
