"""Supabase (PostgREST) storage backend for the `economic_indicators` table.

This module never reads `os.environ` directly -- like every other module
in this codebase, it obtains `SUPABASE_URL`/`SUPABASE_KEY` via
`secrets.get_key()` only, and only at call time (never at import time, so
--dry-run and --list-required-keys never require these env vars to be
set). Never called at all in --dry-run mode; main.py substitutes a
`[DRY-WRITE]` print line instead of calling into this module.

All requests go through `fetchers/_http.py`'s `request_with_retry` --
same retry/backoff/masking pattern already used by every fetcher.
"""

from __future__ import annotations

import datetime as _dt

import secrets
from errors import FetchError
from fetchers import _http

# Referenced by main.py for --list-required-keys / startup validation.
REQUIRED_ENV_VARS = ["SUPABASE_URL", "SUPABASE_KEY"]

_TABLE = "economic_indicators"


def _base_url() -> str:
    supabase_url = secrets.get_key("SUPABASE_URL")
    return f"{supabase_url}/rest/v1/{_TABLE}"


def _auth_headers() -> dict:
    supabase_key = secrets.get_key("SUPABASE_KEY")
    return {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }


def upsert_rows(rows: list[dict]) -> None:
    """POST `rows` to PostgREST with upsert semantics: on_conflict on
    (indicator_id, period), Prefer: resolution=merge-duplicates.

    Each row must already include every non-default column; `updated_at`
    is set here (not by the caller) to the current UTC timestamp, since
    the column's `default now()` only fires on INSERT -- on the
    conflict-update path it must be set explicitly or it would stay stale.

    Raises FetchError with a secrets.mask()-ed message on failure. Never
    called in --dry-run mode (main.py handles that by skipping this
    function entirely, not by mocking it here).
    """
    if not rows:
        return

    now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
    payload = [{**row, "updated_at": now_iso} for row in rows]

    headers = dict(_auth_headers())
    headers["Prefer"] = "resolution=merge-duplicates"

    try:
        _http.request_with_retry(
            "POST",
            _base_url(),
            params={"on_conflict": "indicator_id,period"},
            json_body=payload,
            headers=headers,
        )
    except FetchError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize any unexpected failure
        raise FetchError(secrets.mask(f"supabase_client.upsert_rows: {exc}")) from exc


def delete_before(indicator_id: str, cutoff_period: str) -> None:
    """DELETE rows for `indicator_id` where period < `cutoff_period`
    (lexicographic text comparison -- this project's period label formats,
    YYYY-MM / YYYYQn / YYYY, are already zero-padded and sort correctly as
    text, the same property sliding_window relies on for chronological
    sort). Trims previously-stored rows that fall outside the current
    retention window.

    Raises FetchError with a secrets.mask()-ed message on failure.
    """
    try:
        _http.request_with_retry(
            "DELETE",
            _base_url(),
            params={
                "indicator_id": f"eq.{indicator_id}",
                "period": f"lt.{cutoff_period}",
            },
            headers=_auth_headers(),
        )
    except FetchError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize any unexpected failure
        raise FetchError(secrets.mask(f"supabase_client.delete_before: {exc}")) from exc
