"""Korea Customs Service (관세청) trade statistics fetcher -- data.go.kr,
NOT the UNI-PASS customs portal.

## What research confirmed (real, evidenced)
Three distinct registered data.go.kr services were found under the
`apis.data.go.kr/1220000/...` namespace (auth via `serviceKey`):
  - 관세청_수출입총괄(GW), data.go.kr id 15102108
    -> https://www.data.go.kr/data/15102108/openapi.do
    (aggregate monthly trade balance / exports / imports)
  - 관세청_품목별 수출입실적(GW), data.go.kr id 15101609
    -> https://www.data.go.kr/data/15101609/openapi.do
    (HS-code-level item trade stats, 2/4/6/10-digit HS)
  - 관세청_품목별 국가별 수출입실적(GW), data.go.kr id 15100475, with a
    confirmed live endpoint path:
    `apis.data.go.kr/1220000/nitemtrade/getNitemtradeList`
    (item x country combined -- not directly what we need, but confirms
    the namespace/path convention used by this API family)

## What is genuinely unresolved (why this module raises NotImplementedError)
The exact operation path + parameter names for the two services we
actually need (15102108 aggregate trade balance/exports/imports, and
15101609 item-level HS-code stats) are NOT confirmed. data.go.kr's
landing pages for both only expose a Swagger spec behind on-page images
and a downloadable `관세청조회코드_v1.3.xlsx` reference doc -- neither
was fetchable by this module's author's tools, and no third-party
sample code documenting the exact operation name (analogous to the
nitemtrade example above) was found for these two specific services.
Per this project's rule against fabricating a plausible-looking but
unverified endpoint shape, `fetch()` below raises NotImplementedError
for trade_balance / exports_total / imports_total rather than guess an
operation path.

For the three HS/MTI-code item indicators (export_automobile_yoy,
export_semiconductor_yoy, export_shipbuilding_yoy), Korea's trade stats
in fact classify by MTI code, not a single HS heading, confirming the
suspicion in indicators.yaml's own header comment. Legacy MTI codes were
found (831=반도체, 741/7411=자동차, 746/7461-7464=선박) but research
also surfaced that Korea's MTI classification underwent a major
restructuring effective the June 2026 monthly trade release (15 ->
20 major categories, semiconductors split into memory/system,
memory further split into D램/낸드; automobiles reorganized by vehicle
type/powertrain) -- and today's date (see indicators.yaml provenance
comments) is after that change, so those legacy codes are considered
unreliable rather than merely "might become stale." indicators.yaml
leaves all six customs entries as "TODO" rather than encode a code this
module cannot respect precisely; the guard below reflects that.

If/when this is completed: get an API key, download & read
관세청조회코드_v1.3.xlsx from the 15102108 and 15101609 pages, confirm
the operation path + param names, and confirm current (post-June-2026)
MTI codes against KITA's stat.kita.net MTI code table before wiring up
the HS/MTI-based indicators.
"""

from __future__ import annotations

from errors import FetchError

from . import _http  # noqa: F401  -- imported for when this module is completed

REQUIRED_ENV_VAR = "CUSTOMS_API_KEY"

_NAMESPACE_BASE = "https://apis.data.go.kr/1220000"  # confirmed namespace; operation path TODO


def fetch(indicator: dict, api_key: str) -> list[dict]:
    series_id = indicator.get("series_id")
    if not series_id or series_id == "TODO":
        raise FetchError(
            f"customs.fetch: no series_id configured for {indicator.get('id')!r} "
            "(see fetchers/customs.py module docstring: exact data.go.kr operation "
            "path for Korea Customs trade statistics was not confirmed)"
        )

    # VERIFY: this module has never resolved an operation path/param set
    # for any customs indicator (see module docstring). If series_id was
    # ever manually set to something non-"TODO" without this module also
    # being completed, fail loudly rather than send a fabricated request.
    raise NotImplementedError(
        "customs.fetch: Korea Customs (data.go.kr, service 15102108/15101609 under "
        "apis.data.go.kr/1220000) operation path and parameters are unresolved -- "
        "see fetchers/customs.py module docstring (# VERIFY) for what to check "
        "before implementing this."
    )
