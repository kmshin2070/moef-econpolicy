"""Shared HTTP helper. This is the ONLY place retry logic lives -- no
fetcher module (nor supabase_client.py) should call `requests.get`/`post`/
`delete` (or any other transport) on its own; they must all go through
`request_with_retry` (or its thin `get_with_retry` wrapper).
"""

from __future__ import annotations

import time

import requests

import secrets
from errors import FetchError

DEFAULT_BACKOFF = (1, 2, 4)


def request_with_retry(
    method: str,
    url: str,
    params: dict | None = None,
    json_body: dict | list | None = None,
    headers: dict | None = None,
    retries: int = 3,
    backoff=DEFAULT_BACKOFF,
    timeout: int = 15,
) -> requests.Response:
    """Send an HTTP `method` request to `url` with up to 1 initial attempt +
    `retries` retry attempts (4 total by default), sleeping `backoff[i]`
    seconds between attempts.

    `params` is always passed as the `params=` kwarg and `json_body` as the
    `json=` kwarg -- never interpolated into the URL string here -- so that
    if either contains an API key/token it stays out of any raw-string
    logging path in this function. On final failure, raises FetchError with
    a secrets.mask()-ed message. The underlying request is still allowed to
    fail/retry normally; masking never suppresses or alters the retry
    behavior -- it only sanitizes the message of the exception this
    function raises.
    """
    attempts = retries + 1
    last_exc: Exception | None = None

    for attempt in range(attempts):
        try:
            response = requests.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < attempts - 1:
                time.sleep(backoff[min(attempt, len(backoff) - 1)])
            continue

    message = secrets.mask(str(last_exc)) if last_exc is not None else "request failed"
    raise FetchError(f"{method} request failed after {attempts} attempts: {message}")


def get_with_retry(
    url: str,
    params: dict | None = None,
    retries: int = 3,
    backoff=DEFAULT_BACKOFF,
    timeout: int = 15,
) -> requests.Response:
    """GET `url` with the same retry/backoff/masking behavior as
    `request_with_retry` -- kept as a thin wrapper so every existing
    fetcher's `from . import _http` / `_http.get_with_retry(...)` call
    keeps working unchanged."""
    return request_with_retry(
        "GET", url, params=params, retries=retries, backoff=backoff, timeout=timeout
    )
