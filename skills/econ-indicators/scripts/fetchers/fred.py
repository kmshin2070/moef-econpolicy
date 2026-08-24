"""FRED (Federal Reserve Economic Data, St. Louis Fed) fetcher.

series_id values used by this project (see indicators.yaml, all verified
by title/series-ID match against fred.stlouisfed.org search results as of
this writing -- see the inline comments on each indicators.yaml entry):
  - fed_funds_rate -> FEDFUNDS   (monthly, Federal Funds Effective Rate, %)
  - oil_wti        -> MCOILWTICO (monthly average, WTI Cushing, $/Bbl)
  - oil_brent      -> MCOILBRENTEU (monthly average, Brent - Europe, $/Bbl)
  - oil_dubai      -> POILDUBUSDM (monthly, Global price of Dubai Crude,
                       IMF-sourced, $/Bbl)

We deliberately use the *monthly-average* variants (M-prefixed / IMF
monthly "Global price of ..." series) rather than the daily D-prefixed
spot series (DCOILWTICO, DCOILBRENTEU, DFF) because every indicator in
indicators.yaml using this source has frequency: monthly, and mixing a
daily series into a monthly sheet would require ad hoc resampling this
module does not do.
"""

from __future__ import annotations

import secrets
import sheet_layout
from errors import FetchError

from . import _http

REQUIRED_ENV_VAR = "FRED_API_KEY"

_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


def fetch(indicator: dict, api_key: str) -> list[dict]:
    """Fetch a FRED series' observations and return ascending
    {"period", "value"} dicts at the indicator's frequency.

    Auth: api_key is passed as a query parameter (`api_key=`), per FRED's
    REST API convention -- never in the URL path.
    """
    series_id = indicator.get("series_id")
    frequency = indicator.get("frequency")
    if not series_id or series_id == "TODO":
        raise FetchError(f"fred.fetch: no series_id configured for {indicator.get('id')!r}")

    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "asc",
    }

    try:
        response = _http.get_with_retry(_BASE_URL, params=params)
        data = response.json()
    except FetchError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize any parse failure
        raise FetchError(secrets.mask(f"fred.fetch: bad response for {series_id}: {exc}")) from exc

    observations = data.get("observations")
    if observations is None:
        raise FetchError(
            secrets.mask(f"fred.fetch: response missing 'observations' for series {series_id}")
        )

    results = []
    for obs in observations:
        raw_value = obs.get("value")
        if raw_value in (None, "", "."):
            continue  # FRED's convention for a missing data point
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        date_str = obs.get("date")  # "YYYY-MM-DD"
        if not date_str:
            continue
        period = sheet_layout.format_period(date_str, frequency)
        results.append({"period": period, "value": value})

    if not results:
        raise FetchError(
            secrets.mask(f"fred.fetch: no usable observations returned for series {series_id}")
        )

    results.sort(key=lambda r: r["period"])
    return results
