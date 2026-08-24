"""KOSPI/KOSDAQ index fetcher.

Chosen source: data.go.kr-hosted "금융위원회_지수시세정보" (Financial
Services Commission "Index Market Price Info") service, id 15094807
(https://www.data.go.kr/data/15094807/openapi.do), operation
GetMarketIndexInfoService/getStockMarketIndex -- a `serviceKey`-keyed
API, NOT KRX's own unauthenticated MDCSTAT/data.krx.co.kr endpoints.
This is deliberate: this project's design assumes each source needs its
own `*_API_KEY`, so a keyed data.go.kr service was preferred over KRX's
unauthenticated public endpoints for architectural consistency with the
other four fetchers.

Base URL and request params confirmed via a working third-party sample
implementation (blog walkthrough of this exact operation), since the
data.go.kr landing page itself only exposes a Swagger spec behind a
Word-doc download this module's author could not open:
  https://velog.io/@ykh9759/Spring-Boot로-오픈-API사용하기

  GET http://apis.data.go.kr/1160100/service/GetMarketIndexInfoService/getStockMarketIndex
  params: serviceKey, numOfRows, pageNo, resultType=json,
          idxNm (e.g. "코스피"), beginBasDt, endBasDt (both yyyyMMdd)
  response: response.body.items.item[] with fields incl.
          basDt (yyyyMMdd), idxNm, clpr (closing price)

series_id in indicators.yaml is the `idxNm` value to request:
  "코스피" for kospi, "코스닥" for kosdaq.
"""

from __future__ import annotations

import datetime as _dt

import secrets
from errors import FetchError

from . import _http

REQUIRED_ENV_VAR = "KRX_API_KEY"

_BASE_URL = "http://apis.data.go.kr/1160100/service/GetMarketIndexInfoService/getStockMarketIndex"
_PAGE_SIZE = 500
_MAX_PAGES = 10


def fetch(indicator: dict, api_key: str) -> list[dict]:
    """Fetch daily KOSPI/KOSDAQ closing values and reduce to the
    indicator's frequency (monthly: last trading day of each month)."""
    idx_nm = indicator.get("series_id")
    if not idx_nm or idx_nm == "TODO":
        raise FetchError(f"krx.fetch: no series_id (idxNm) configured for {indicator.get('id')!r}")

    frequency = indicator.get("frequency")
    if frequency != "monthly":
        # Only the monthly (month-end close) case is implemented -- both
        # current indicators.yaml entries (kospi, kosdaq) are monthly.
        raise NotImplementedError(
            f"krx.fetch: frequency {frequency!r} not implemented (only monthly is)"
        )

    end_date = _dt.date.today()
    begin_date = end_date - _dt.timedelta(days=365 * 11)  # comfortably over 10y retention

    daily_records: list[dict] = []
    for page_no in range(1, _MAX_PAGES + 1):
        params = {
            "serviceKey": api_key,
            "numOfRows": _PAGE_SIZE,
            "pageNo": page_no,
            "resultType": "json",
            "idxNm": idx_nm,  # VERIFY: exact idxNm string may have changed
            # in KRX's Dec-2024 index-name scheme revision -- confirm this
            # value still matches a real index before first live run.
            "beginBasDt": begin_date.strftime("%Y%m%d"),
            "endBasDt": end_date.strftime("%Y%m%d"),
        }

        try:
            response = _http.get_with_retry(_BASE_URL, params=params)
            data = response.json()
        except FetchError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise FetchError(
                secrets.mask(f"krx.fetch: bad response for idxNm={idx_nm}: {exc}")
            ) from exc

        body = (data.get("response") or {}).get("body") or {}
        items_container = body.get("items")
        items = []
        if isinstance(items_container, dict):
            raw_item = items_container.get("item")
            if isinstance(raw_item, list):
                items = raw_item
            elif isinstance(raw_item, dict):
                items = [raw_item]
        if not items:
            break

        daily_records.extend(items)
        if len(items) < _PAGE_SIZE:
            break  # last page

    if not daily_records:
        raise FetchError(
            secrets.mask(f"krx.fetch: no data returned for idxNm={idx_nm} in requested range")
        )

    # Reduce daily records to one value per calendar month: the record
    # with the latest basDt in that month (month-end close).
    by_month: dict[str, tuple[str, float]] = {}
    for rec in daily_records:
        bas_dt = rec.get("basDt")
        clpr = rec.get("clpr")
        if not bas_dt or clpr in (None, ""):
            continue
        try:
            value = float(clpr)
        except (TypeError, ValueError):
            continue
        period = f"{bas_dt[0:4]}-{bas_dt[4:6]}"
        existing = by_month.get(period)
        if existing is None or bas_dt > existing[0]:
            by_month[period] = (bas_dt, value)

    if not by_month:
        raise FetchError(
            secrets.mask(f"krx.fetch: no usable (basDt, clpr) pairs for idxNm={idx_nm}")
        )

    results = [{"period": period, "value": val[1]} for period, val in by_month.items()]
    results.sort(key=lambda r: r["period"])
    return results
