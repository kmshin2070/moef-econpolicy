#!/usr/bin/env python3
"""CLI entry point for the econ-indicators backend.

Reads indicators.yaml, fetches fresh data for every fully-configured
indicator, trims it to each indicator's retention window via
periods.sliding_window, and upserts the kept rows straight into the
Supabase `economic_indicators` table (plus deleting anything outside the
window). Each run recomputes the retention window from scratch and
upserts idempotently -- no external state input is needed. stdout only
ever carries short non-sensitive progress lines -- never the JSON
payload, never a raw exception, never a secret value.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import yaml  # noqa: E402

import periods  # noqa: E402
import secrets  # noqa: E402
import supabase_client  # noqa: E402
from errors import ConfigError  # noqa: E402

_TODO = "TODO"


def load_indicators_file(path: Path) -> dict:
    if not path.exists():
        raise ConfigError(f"indicators file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or "indicators" not in data:
        raise ConfigError(f"indicators file {path} missing top-level 'indicators' key")
    return data


def pending_fields(indicator: dict) -> list[str]:
    """Return which of series_id/org_id are still literally "TODO", or
    [] if the indicator is fully configured and safe to fetch."""
    missing = []
    if indicator.get("series_id", _TODO) == _TODO:
        missing.append("series_id")
    if "org_id" in indicator and indicator.get("org_id") == _TODO:
        missing.append("org_id")
    return missing


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="econ-indicators backend runner")
    parser.add_argument(
        "--indicators-file",
        default=str(SCRIPT_DIR.parent / "indicators.yaml"),
        help="Path to indicators.yaml (default: indicators.yaml next to skills/econ-indicators/, i.e. one level above scripts/)",
    )
    parser.add_argument(
        "--output-out",
        default=None,
        help="Path to write the result JSON (never written to stdout). Required unless --list-required-keys.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use tests/fixtures/mock_fetchers.py instead of the real registry, and print "
        "[DRY-WRITE] lines instead of writing to Supabase",
    )
    parser.add_argument(
        "--list-required-keys",
        action="store_true",
        help="Print required env var NAMES for this indicators.yaml's sources and exit",
    )
    return parser


def _load_registry(dry_run: bool):
    if dry_run:
        from tests.fixtures import mock_fetchers as registry_module
    else:
        import fetchers as registry_module
    return registry_module


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)

    if not args.list_required_keys and not args.output_out:
        print("[ABORT] --output-out is required unless --list-required-keys is passed")
        return 2

    try:
        indicators_data = load_indicators_file(Path(args.indicators_file))
    except Exception as exc:  # noqa: BLE001
        print(f"[ABORT] failed to load indicators file: {secrets.mask(str(exc))}")
        return 2

    indicators = indicators_data.get("indicators", [])
    settings = indicators_data.get("settings", {}) or {}
    retain_periods_by_frequency = settings.get("retain_periods_by_frequency", {})

    try:
        registry_module = _load_registry(args.dry_run)
    except Exception as exc:  # noqa: BLE001
        print(f"[ABORT] failed to load fetcher registry: {secrets.mask(str(exc))}")
        return 2

    registry = registry_module.REGISTRY

    if args.list_required_keys:
        required = secrets.discover_required_env_vars(indicators, registry)
        required |= set(supabase_client.REQUIRED_ENV_VARS)
        for name in sorted(required):
            print(name)
        return 0

    if not args.dry_run:
        # --- startup validation 1: every source must exist in registry ---
        unknown = {}
        for ind in indicators:
            src = ind.get("source")
            if src not in registry:
                unknown.setdefault(src, []).append(ind.get("id", "?"))
        if unknown:
            print("[ABORT] unknown source(s) referenced in indicators.yaml:")
            for src, ids in sorted(unknown.items(), key=lambda kv: str(kv[0])):
                print(f"  source={src!r} used by: {', '.join(ids)}")
            return 2

        # --- startup validation 2: every REQUIRED_ENV_VAR must be present ---
        # Supabase is a single fixed storage backend now (not pluggable per
        # indicator like fetchers), so its two env vars are unconditionally
        # required alongside whichever fetcher keys the active sources need.
        required_vars = secrets.discover_required_env_vars(indicators, registry)
        required_vars |= set(supabase_client.REQUIRED_ENV_VARS)
        presence = secrets.check_env_vars_present(required_vars)
        missing = sorted(name for name, present in presence.items() if not present)
        if missing:
            print("[ABORT] missing required environment variable(s):")
            for name in missing:
                print(f"  {name}")
            return 2

    succeeded = 0
    failures: list[dict] = []
    pending_configuration: list[dict] = []
    written: list[dict] = []

    for ind in indicators:
        ind_id = ind["id"]
        category = ind["category"]
        name = ind.get("name", ind_id)
        frequency = ind["frequency"]
        source = ind["source"]

        missing = pending_fields(ind)
        if missing:
            print(f"[SKIP] {ind_id} (pending_configuration)")
            pending_configuration.append(
                {"id": ind_id, "category": category, "name": name, "missing": missing}
            )
            continue

        fetch_fn, required_env_var = registry_module.get_fetcher(source)

        try:
            if args.dry_run:
                api_key = "dry-run-unused"
            else:
                api_key = secrets.get_key(required_env_var)
            raw_results = fetch_fn(ind, api_key)
        except Exception as exc:  # noqa: BLE001 - never let one indicator abort the run
            print(f"[FAIL] {ind_id}")
            failures.append(
                {
                    "id": ind_id,
                    "category": category,
                    "name": name,
                    "error": secrets.mask(str(exc)),
                }
            )
            continue

        kept, _dropped = periods.sliding_window(
            [r["period"] for r in raw_results], frequency, retain_periods_by_frequency
        )
        value_by_period = {r["period"]: r["value"] for r in raw_results}

        rows = [
            {
                "indicator_id": ind_id,
                "category": category,
                "name_ko": name,
                "period": period,
                "frequency": frequency,
                "value": value_by_period[period],
                "unit": ind.get("unit", ""),
                "source": source,
            }
            for period in kept
        ]

        if not rows:
            # Fetch succeeded but nothing survived the retention window --
            # nothing to write, but not a failure either.
            succeeded += 1
            print(f"[OK] {ind_id}")
            written.append({"id": ind_id, "category": category, "periods_written": 0})
            continue

        try:
            if args.dry_run:
                print(f"[DRY-WRITE] {ind_id}: {len(rows)} periods")
            else:
                supabase_client.upsert_rows(rows)
                # `kept` is already chronologically ascending (sliding_window's
                # contract), so its first element is the oldest kept period.
                cutoff_period = kept[0]
                supabase_client.delete_before(ind_id, cutoff_period)
        except Exception as exc:  # noqa: BLE001 - a write failure is still a failure
            print(f"[FAIL] {ind_id}")
            failures.append(
                {
                    "id": ind_id,
                    "category": category,
                    "name": name,
                    "error": secrets.mask(str(exc)),
                }
            )
            continue

        succeeded += 1
        print(f"[OK] {ind_id}")
        written.append({"id": ind_id, "category": category, "periods_written": len(rows)})

    total = len(indicators)
    failed_count = len(failures)
    pending_count = len(pending_configuration)

    summary_ko = (
        f"이번 주 경제지표 업데이트 결과: {total}개 중 {succeeded}개 성공, "
        f"{failed_count}개 실패, {pending_count}개는 설정 미완료로 제외되었습니다."
    )
    if failures:
        fail_names = ", ".join(f["id"] for f in failures[:10])
        summary_ko += f" 실패 항목: {fail_names}."
    if pending_configuration:
        pending_names = ", ".join(p["id"] for p in pending_configuration[:10])
        summary_ko += f" 설정 미완료 항목: {pending_names}."

    output = {
        "run_metadata": {
            "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "total": total,
            "succeeded": succeeded,
            "failed": failed_count,
            "pending_configuration": pending_count,
        },
        "written": written,
        "failures": failures,
        "pending_configuration": pending_configuration,
        "summary_ko": summary_ko,
    }

    output_path = Path(args.output_out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(
        f"[DONE] total={total} succeeded={succeeded} failed={failed_count} "
        f"pending_configuration={pending_count}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
