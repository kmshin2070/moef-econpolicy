"""BOK (Bank of Korea) ECOS Open API fetcher.

indicators.yaml encoding for this source: `series_id` =
"<stat_code>/<item_code1>[/<item_code2>...]" (통계표코드 followed by one
or more 통계항목코드, matching ECOS's own StatisticSearch URL segment
order).

ECOS's REST convention places the auth key as a URL PATH segment (not a
query parameter), per the official API guide, confirmed via live calls
made with the public "sample" auth key during research for this project:

  GET https://ecos.bok.or.kr/api/StatisticSearch/{인증키}/{요청유형}/{언어구분}
      /{요청시작건수}/{요청종료건수}/{통계표코드}/{주기}/{검색시작일자}/{검색종료일자}
      /{통계항목코드1}/{통계항목코드2}/{통계항목코드3}/{통계항목코드4}

`주기` (cycle) is one letter: D=daily, A=annual, Q=quarterly, M=monthly.
Most indicators' cycle matches their `frequency` directly, but a few
BOK tables only publish at a *finer* cycle than the indicator's declared
frequency (e.g. exchange rates / treasury yields are daily-only tables
in ECOS) -- `_RECIPES` below overrides the request cycle for those and
this module reduces the daily series to month-end values itself (same
pattern as fetchers/krx.py's month-end reduction).

Several other indicators (전산업생산지수 MoM/QoQ, CPI MoM/YoY, 취업자
수 증감 YoY) only exist in ECOS as a raw index/level series -- there is
no separately stored %-change or diff series -- so this module computes
the requested transform itself from consecutive raw observations
(`_RECIPES[...]["transform"]`). This is a documented, live-verified
design choice (see research notes below), not a guess.

This module builds each request URL with no query params (since
everything, including the key, is already in the path) -- secrets.mask()
still finds and redacts the key wherever it appears (path segment or
query string alike), since it works on the *value*, not the position.

## Research provenance (live-verified against ECOS's public "sample" key
## and cross-checked against ECOS's KeyStatisticList 100대 통계지표
## snapshot; see indicators.yaml inline comments for the per-indicator
## stat/item codes and confidence notes)

# VERIFY (exchange_rate_usdkrw, treasury_10y, treasury_3y): the BOK
# tables found (731Y001 원/달러, 817Y002 국고채) are explicitly
# daily-only ("일별") -- a monthly-cycle query returned no data during
# research. A monthly/quarterly/annual companion table (721Y001) may
# exist for market rates but its exact 국고채(3y/10y) item codes were
# not confirmed within the research budget (the public "sample" key
# caps results at 10 rows, blocking full item-list pagination). This
# module instead requests the daily series and reduces to a month-end
# value client-side -- confirm this is the intended convention (vs. a
# monthly average) before first live run.

# VERIFY (ind_prod_qoq_from_monthly): "월간 데이터의 전분기대비" is
# interpreted here as: group the monthly 전산업생산지수 raw index into
# quarters, compute each complete quarter's average vs the prior
# quarter's average, and repeat that one QoQ% value across the 3 months
# of the quarter it describes. indicators.yaml's own original header
# comment already flagged this indicator (vs.
# ind_prod_qoq_from_quarterly) as needing clarification from the
# requesting team -- that ambiguity is about the *intended metric*, not
# the underlying data source, which research did confirm (901Y033/A00/2).
"""

from __future__ import annotations

import datetime as _dt

import secrets
from errors import FetchError

from . import _http

REQUIRED_ENV_VAR = "BOK_API_KEY"

_BASE_URL = "https://ecos.bok.or.kr/api/StatisticSearch"
_REQUEST_TYPE = "json"
_LANG = "kr"
_ROW_START = 1
_ROW_END = 500  # comfortably covers 10y monthly (120) + buffer
_ROW_END_DAILY = 4500  # ~12y of trading/business days

_FREQUENCY_TO_CYCLE = {"monthly": "M", "quarterly": "Q", "annual": "A"}

# Per-indicator overrides for the (rare) cases where the request cycle
# must differ from the indicator's declared frequency, and/or the raw
# ECOS series needs a client-side transform to become the requested
# metric. See module docstring for the research basis of each entry.
_RECIPES = {
    "ind_prod_mom": {"cycle": "M", "transform": "pct_change_1"},
    "ind_prod_qoq_from_monthly": {"cycle": "M", "transform": "qoq_pct_repeated_monthly"},
    "ind_prod_qoq_from_quarterly": {"cycle": "Q", "transform": "pct_change_1"},
    "cpi_mom": {"cycle": "M", "transform": "pct_change_1"},
    "cpi_yoy": {"cycle": "M", "transform": "pct_change_12"},
    "employment_change_yoy": {"cycle": "M", "transform": "diff_12"},
    "exchange_rate_usdkrw": {"cycle": "D", "reduce": "month_end"},
    "treasury_10y": {"cycle": "D", "reduce": "month_end"},
    "treasury_3y": {"cycle": "D", "reduce": "month_end"},
}


def _date_range_for_cycle(cycle: str) -> tuple[str, str]:
    today = _dt.date.today()
    if cycle == "D":
        start = today.replace(year=today.year - 12)
        return start.strftime("%Y%m%d"), today.strftime("%Y%m%d")
    if cycle == "M":
        start = today.replace(year=today.year - 15, day=1)
        return start.strftime("%Y%m"), today.strftime("%Y%m")
    if cycle == "Q":
        start_year = today.year - 15
        end_quarter = (today.month - 1) // 3 + 1
        return f"{start_year}Q1", f"{today.year}Q{end_quarter}"
    if cycle == "A":
        return str(today.year - 15), str(today.year)
    raise ValueError(f"unknown cycle: {cycle!r}")


def _native_period(time_value: str, cycle: str) -> str:
    """Normalize an ECOS TIME value to this project's period label for
    that cycle: D -> "YYYY-MM-DD", M -> "YYYY-MM", Q -> "YYYYQn" (ECOS
    already returns this shape), A -> "YYYY"."""
    time_value = time_value.strip()
    if cycle == "D":
        if len(time_value) == 8:
            return f"{time_value[0:4]}-{time_value[4:6]}-{time_value[6:8]}"
        raise ValueError(f"unexpected daily TIME shape from ECOS: {time_value!r}")
    if cycle == "M":
        if len(time_value) == 6:
            return f"{time_value[0:4]}-{time_value[4:6]}"
        raise ValueError(f"unexpected monthly TIME shape from ECOS: {time_value!r}")
    if cycle == "Q":
        if "Q" in time_value.upper():
            return time_value.upper()
        raise ValueError(f"unexpected quarterly TIME shape from ECOS: {time_value!r}")
    if cycle == "A":
        if len(time_value) == 4:
            return time_value
        raise ValueError(f"unexpected annual TIME shape from ECOS: {time_value!r}")
    raise ValueError(f"unknown cycle: {cycle!r}")


def _fetch_raw_series(stat_code: str, item_codes: list[str], cycle: str, api_key: str) -> list[dict]:
    """Call ECOS StatisticSearch and return ascending [{"period", "value"}]
    at the native `cycle` grain (no transform, no reduction)."""
    row_end = _ROW_END_DAILY if cycle == "D" else _ROW_END
    start_date, end_date = _date_range_for_cycle(cycle)

    url_segments = [
        _BASE_URL,
        api_key,
        _REQUEST_TYPE,
        _LANG,
        str(_ROW_START),
        str(row_end),
        stat_code,
        cycle,
        start_date,
        end_date,
        *item_codes,
    ]
    url = "/".join(url_segments)

    try:
        response = _http.get_with_retry(url)
        data = response.json()
    except FetchError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise FetchError(
            secrets.mask(f"bok_ecos.fetch: bad response for stat_code={stat_code}: {exc}")
        ) from exc

    result_block = data.get("RESULT")
    if result_block and result_block.get("CODE") not in (None, "INFO-000"):
        raise FetchError(
            secrets.mask(
                f"bok_ecos.fetch: ECOS error for stat_code={stat_code}: "
                f"{result_block.get('CODE')} {result_block.get('MESSAGE')}"
            )
        )

    search_block = data.get("StatisticSearch")
    if not search_block or "row" not in search_block:
        raise FetchError(
            secrets.mask(
                f"bok_ecos.fetch: no 'StatisticSearch.row' in response for stat_code={stat_code}"
            )
        )

    results = []
    for row in search_block["row"]:
        time_value = row.get("TIME")
        raw_value = row.get("DATA_VALUE")
        if not time_value or raw_value in (None, ""):
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        try:
            period = _native_period(time_value, cycle)
        except ValueError:
            continue
        results.append({"period": period, "value": value})

    results.sort(key=lambda r: r["period"])
    return results


def _reduce_daily_to_month_end(daily: list[dict]) -> list[dict]:
    """daily: ascending [{"period": "YYYY-MM-DD", "value": float}].
    Returns ascending [{"period": "YYYY-MM", "value": <last day's value>}]."""
    by_month: dict[str, tuple[str, float]] = {}
    for entry in daily:
        day_period = entry["period"]  # "YYYY-MM-DD"
        month_period = day_period[0:7]
        existing = by_month.get(month_period)
        if existing is None or day_period > existing[0]:
            by_month[month_period] = (day_period, entry["value"])
    out = [{"period": p, "value": v[1]} for p, v in by_month.items()]
    out.sort(key=lambda r: r["period"])
    return out


def _pct_change(series: list[dict], lag: int) -> list[dict]:
    """series: ascending [{"period", "value"}] at a uniform, contiguous
    cycle. Returns pct-change vs `lag` periods earlier, by *index*
    (assumes no gaps in the raw series, which ECOS's own tables are for
    these indicators)."""
    out = []
    for i in range(lag, len(series)):
        prev = series[i - lag]["value"]
        curr = series[i]["value"]
        if prev == 0:
            continue
        pct = (curr / prev - 1.0) * 100.0
        out.append({"period": series[i]["period"], "value": round(pct, 4)})
    return out


def _diff(series: list[dict], lag: int) -> list[dict]:
    out = []
    for i in range(lag, len(series)):
        out.append(
            {"period": series[i]["period"], "value": series[i]["value"] - series[i - lag]["value"]}
        )
    return out


def _quarter_of_month_period(month_period: str) -> str:
    year, month = month_period.split("-")
    quarter = (int(month) - 1) // 3 + 1
    return f"{year}Q{quarter}"


def _qoq_pct_repeated_monthly(monthly_series: list[dict]) -> list[dict]:
    """See module docstring VERIFY note. Groups monthly index values into
    complete (3-month) quarters, computes each complete quarter's
    average vs the prior complete quarter's average, then repeats that
    one QoQ% figure across the 3 monthly period labels in that quarter."""
    by_quarter: dict[str, list[float]] = {}
    for entry in monthly_series:
        q = _quarter_of_month_period(entry["period"])
        by_quarter.setdefault(q, []).append(entry["value"])

    complete_quarters = {q: vals for q, vals in by_quarter.items() if len(vals) == 3}
    quarter_avg = {q: sum(vals) / 3.0 for q, vals in complete_quarters.items()}
    sorted_quarters = sorted(quarter_avg.keys(), key=lambda q: (q[0:4], q[5:]))

    qoq_by_quarter: dict[str, float] = {}
    for i in range(1, len(sorted_quarters)):
        prev_q, curr_q = sorted_quarters[i - 1], sorted_quarters[i]
        prev_avg = quarter_avg[prev_q]
        if prev_avg == 0:
            continue
        qoq_by_quarter[curr_q] = round((quarter_avg[curr_q] / prev_avg - 1.0) * 100.0, 4)

    out = []
    for entry in monthly_series:
        q = _quarter_of_month_period(entry["period"])
        if q in qoq_by_quarter:
            out.append({"period": entry["period"], "value": qoq_by_quarter[q]})
    return out


def fetch(indicator: dict, api_key: str) -> list[dict]:
    series_id = indicator.get("series_id")
    frequency = indicator.get("frequency")
    indicator_id = indicator.get("id")
    if not series_id or series_id == "TODO":
        raise FetchError(f"bok_ecos.fetch: no series_id configured for {indicator_id!r}")

    parts = [p for p in series_id.split("/") if p]
    if len(parts) < 2:
        raise FetchError(
            f"bok_ecos.fetch: series_id {series_id!r} for {indicator_id!r} must be "
            "\"<stat_code>/<item_code1>[/...]\""
        )
    stat_code, item_codes = parts[0], parts[1:]

    recipe = _RECIPES.get(indicator_id, {})
    cycle = recipe.get("cycle") or _FREQUENCY_TO_CYCLE.get(frequency)
    if cycle is None:
        raise NotImplementedError(f"bok_ecos.fetch: unsupported frequency {frequency!r}")

    raw = _fetch_raw_series(stat_code, item_codes, cycle, api_key)
    if not raw:
        raise FetchError(
            secrets.mask(f"bok_ecos.fetch: no usable observations for series_id={series_id}")
        )

    reduce = recipe.get("reduce")
    if reduce == "month_end":
        raw = _reduce_daily_to_month_end(raw)

    transform = recipe.get("transform")
    if transform == "pct_change_1":
        results = _pct_change(raw, lag=1)
    elif transform == "pct_change_12":
        results = _pct_change(raw, lag=12)
    elif transform == "diff_12":
        results = _diff(raw, lag=12)
    elif transform == "qoq_pct_repeated_monthly":
        results = _qoq_pct_repeated_monthly(raw)
    elif transform is None:
        results = raw
    else:
        raise NotImplementedError(f"bok_ecos.fetch: unknown transform {transform!r}")

    if not results:
        raise FetchError(
            secrets.mask(
                f"bok_ecos.fetch: transform produced no observations for series_id={series_id} "
                f"(indicator {indicator_id!r}, transform={transform!r})"
            )
        )

    results.sort(key=lambda r: r["period"])
    return results
