"""KOSIS (국가통계포털) Open API fetcher.

indicators.yaml encoding for this source: `series_id` = tblId (통계표
ID), `org_id` = orgId (기관코드).

Endpoint: this module calls KOSIS's parameter-based statistical data
endpoint, `https://kosis.kr/openapi/Param/statisticsParameterData.do`
(method=getList, format=json, jsonVD=Y, apiKey, orgId, tblId, itmId,
objL1.., prdSe, startPrdDe, endPrdDe). This is KOSIS's standard
documented data-retrieval endpoint shape.
# VERIFY: only the *sibling* list-search endpoint
# (kosis.kr/openapi/statisticsList.do) was confirmed reachable during
# research (it returned a real "인증KEY값이 누락되었습니다" error
# confirming the method/format/jsonVD/apiKey param convention) --
# the data-retrieval endpoint path/params above were not independently
# confirmed against a live call (no API key was available during
# research). Confirm this exact path with a real key before first run.

employment_rate (고용률, monthly): resolved to orgId=101 (통계청),
tblId=DT_1DA7002S ("성별/연령계층별 경제활동인구총괄"), found via
multiple corroborating search-result snippets citing this exact
orgId+tblId pair.
# VERIFY: this table contains many items (경제활동인구, 참가율,
# 취업자, 실업자, 실업률, 고용률, ...), so a single numeric itmId to
# isolate "고용률" alone was NOT found/verified. This module instead
# fetches without pinning itmId and filters the returned rows by
# ITM_NM containing "고용률" client-side -- confirm this actually
# isolates the right row (and that no objL1 classification param is
# mandatory for this table) with a real test call before first run.

government_debt / government_debt_to_gdp (국가채무 D1 / D1-to-GDP,
annual): NOT found as a discrete KOSIS 국가승인통계 series after a real
search effort -- e-나라지표's own citations for these indicators point
to MOEF's 국가채무관리보고서/계획 directly, not KOSIS, and no matching
entry was found in narastat.kr's approved-statistics registry either.
A stronger real lead exists outside KOSIS: 기획재정부 열린재정 Open
Fiscal Data (https://www.openfiscaldata.go.kr), which has its own
serviceKey-keyed OpenAPI and a dedicated 국가채무(D1/D2/D3) page
(openfiscaldata.go.kr/op/ko/sm/UOPKOSMA20). Left as "TODO" in
indicators.yaml rather than fabricated -- if this project ever adds an
"openfiscaldata" source it should be re-pointed there.
"""

from __future__ import annotations

import secrets
from errors import FetchError

from . import _http

REQUIRED_ENV_VAR = "KOSIS_API_KEY"

_BASE_URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"

_FREQUENCY_TO_PRDSE = {"monthly": "M", "quarterly": "Q", "annual": "Y"}


def _format_period_from_prd_de(prd_de: str, frequency: str) -> str:
    """KOSIS PRD_DE values are typically "YYYYMM" (monthly), "YYYYQn" or
    "YYYY0n" (quarterly), "YYYY" (annual) depending on table -- handle
    the common shapes defensively."""
    prd_de = prd_de.strip()
    if frequency == "monthly":
        if len(prd_de) == 6:
            return f"{prd_de[0:4]}-{prd_de[4:6]}"
        raise ValueError(f"unexpected monthly PRD_DE shape: {prd_de!r}")
    if frequency == "quarterly":
        if len(prd_de) == 5:
            return f"{prd_de[0:4]}Q{prd_de[4:5]}"
        if "Q" in prd_de.upper():
            return prd_de.upper()
        raise ValueError(f"unexpected quarterly PRD_DE shape: {prd_de!r}")
    if frequency == "annual":
        if len(prd_de) == 4:
            return prd_de
        raise ValueError(f"unexpected annual PRD_DE shape: {prd_de!r}")
    raise ValueError(f"unknown frequency: {frequency!r}")


def fetch(indicator: dict, api_key: str) -> list[dict]:
    tbl_id = indicator.get("series_id")
    org_id = indicator.get("org_id")
    frequency = indicator.get("frequency")

    if not tbl_id or tbl_id == "TODO" or not org_id or org_id == "TODO":
        raise FetchError(
            f"kosis.fetch: series_id/org_id not configured for {indicator.get('id')!r}"
        )

    prd_se = _FREQUENCY_TO_PRDSE.get(frequency)
    if prd_se is None:
        raise NotImplementedError(f"kosis.fetch: unsupported frequency {frequency!r}")

    params = {
        "method": "getList",
        "apiKey": api_key,
        "itmId": "ALL",  # VERIFY: see module docstring -- filtered client-side below
        "objL1": "ALL",  # VERIFY: may need a specific "total" code, unconfirmed
        "format": "json",
        "jsonVD": "Y",
        "prdSe": prd_se,
        "orgId": org_id,
        "tblId": tbl_id,
    }

    try:
        response = _http.get_with_retry(_BASE_URL, params=params)
        data = response.json()
    except FetchError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise FetchError(
            secrets.mask(f"kosis.fetch: bad response for orgId={org_id} tblId={tbl_id}: {exc}")
        ) from exc

    if isinstance(data, dict) and "err" in data:
        raise FetchError(
            secrets.mask(
                f"kosis.fetch: API error for orgId={org_id} tblId={tbl_id}: "
                f"{data.get('errMsg', data.get('err'))}"
            )
        )
    if not isinstance(data, list):
        raise FetchError(
            secrets.mask(f"kosis.fetch: unexpected response shape for tblId={tbl_id}")
        )

    # For tables with a single unambiguous item (no multi-item filtering
    # needed) this keeps all rows; for tables like employment_rate's
    # DT_1DA7002S (many items in one table) this narrows to the row(s)
    # whose item name matches the indicator's Korean name.
    name_hint = indicator.get("name", "")
    core_hint = name_hint.split("(")[0].strip()  # e.g. "고용률" from "고용률"
    rows = data
    if core_hint:
        name_filtered = [r for r in rows if core_hint in (r.get("ITM_NM") or "")]
        if name_filtered:
            rows = name_filtered

    results = []
    for row in rows:
        prd_de = row.get("PRD_DE")
        raw_value = row.get("DT")
        if not prd_de or raw_value in (None, "", "-"):
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        try:
            period = _format_period_from_prd_de(prd_de, frequency)
        except ValueError:
            continue
        results.append({"period": period, "value": value})

    if not results:
        raise FetchError(
            secrets.mask(
                f"kosis.fetch: no usable observations for orgId={org_id} tblId={tbl_id} "
                f"(item filter matched {len(rows)} row(s))"
            )
        )

    # De-duplicate by period (multiple classification rows can share a
    # period if the client-side ITM_NM filter didn't fully disambiguate)
    # by keeping the last occurrence, then sort ascending.
    by_period = {r["period"]: r["value"] for r in results}
    merged = [{"period": p, "value": v} for p, v in by_period.items()]
    merged.sort(key=lambda r: r["period"])
    return merged
