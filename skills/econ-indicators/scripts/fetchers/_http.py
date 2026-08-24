"""Shared HTTP helper. This is the ONLY place retry logic lives -- no
fetcher module should call `requests.get` (or any other transport) on its
own; they must all go through `get_with_retry`.
"""

from __future__ import annotations

import time

import requests

import secrets
from errors import FetchError

DEFAULT_BACKOFF = (1, 2, 4)


def get_with_retry(
    url: str,
    params: dict | None = None,
    retries: int = 3,
    backoff=DEFAULT_BACKOFF,
    timeout: int = 15,
) -> requests.Response:
    """GET `url` with up to 1 initial attempt + `retries` retry attempts
    (4 total by default), sleeping `backoff[i]` seconds between attempts.

    `params` is always passed as the `params=` kwarg to requests.get --
    never interpolated into the URL string here -- so that if it contains
    an API key it stays out of any raw-string logging path in this
    function. On final failure, raises FetchError with a secrets.mask()-ed
    message. The underlying request is still allowed to fail/retry
    normally; masking never suppresses or alters the retry behavior --
    it only sanitizes the message of the exception this function raises.
    """
    attempts = retries + 1
    last_exc: Exception | None = None

    for attempt in range(attempts):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < attempts - 1:
                time.sleep(backoff[min(attempt, len(backoff) - 1)])
            continue

    message = secrets.mask(str(last_exc)) if last_exc is not None else "request failed"
    raise FetchError(f"GET request failed after {attempts} attempts: {message}")
