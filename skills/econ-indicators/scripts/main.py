#!/usr/bin/env python3
"""CLI entry point for the econ-indicators backend.

Reads indicators.yaml + a sheet-state snapshot, fetches fresh data for
every fully-configured indicator, computes row/column sheet updates via
sheet_layout, and writes one result JSON to --output-out. stdout only
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

import secrets  # noqa: E402
import sheet_layout  # noqa: E402
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


def load_sheet_state(path: str | None) -> dict:
    """Missing path, missing file, or empty file all mean "empty state"
    (first-run bootstrap) -- never an error."""
    if not path:
        return {"tabs": {}}
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return {"tabs": {}}
    with open(p, "r", encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        return {"tabs": {}}
    data = json.loads(text)
    data.setdefault("tabs", {})
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
        "--sheet-state-in",
        default=None,
        help="Path to current-sheet-state JSON (missing/empty => first-run bootstrap)",
    )
    parser.add_argument(
        "--output-out",
        default=None,
        help="Path to write the result JSON (never written to stdout). Required unless --list-required-keys.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use tests/fixtures/mock_fetchers.py instead of the real registry",
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
    header_row = settings.get("header_row", 1)
    retain_periods_by_frequency = settings.get("retain_periods_by_frequency", {})

    try:
        registry_module = _load_registry(args.dry_run)
    except Exception as exc:  # noqa: BLE001
        print(f"[ABORT] failed to load fetcher registry: {secrets.mask(str(exc))}")
        return 2

    registry = registry_module.REGISTRY

    if args.list_required_keys:
        required = secrets.discover_required_env_vars(indicators, registry)
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
        required_vars = secrets.discover_required_env_vars(indicators, registry)
        presence = secrets.check_env_vars_present(required_vars)
        missing = sorted(name for name, present in presence.items() if not present)
        if missing:
            print("[ABORT] missing required environment variable(s):")
            for name in missing:
                print(f"  {name}")
            return 2

    sheet_state = load_sheet_state(args.sheet_state_in)
    tabs_state = sheet_state.get("tabs", {})

    succeeded = 0
    failures: list[dict] = []
    pending_configuration: list[dict] = []
    sheet_updates: dict = {}

    # Group indicators by category, preserving indicators.yaml order.
    categories: dict[str, list[dict]] = {}
    for ind in indicators:
        categories.setdefault(ind["category"], []).append(ind)

    for category, cat_indicators in categories.items():
        tab_grain = sheet_layout.resolve_tab_grain(cat_indicators)
        category_state = tabs_state.get(category, {}) or {}
        existing_periods = set(category_state.get("periods", []) or [])
        existing_rows = category_state.get("rows", {}) or {}
        running_max_row = max(
            [r.get("row", header_row) for r in existing_rows.values()] + [header_row]
        )

        fresh_by_indicator: dict[str, list[dict]] = {}
        row_by_indicator: dict[str, int] = {}
        is_new_row_by_indicator: dict[str, bool] = {}

        for ind in cat_indicators:
            ind_id = ind["id"]
            name = ind.get("name", ind_id)

            missing = pending_fields(ind)
            if missing:
                print(f"[SKIP] {ind_id} (pending_configuration)")
                pending_configuration.append(
                    {"id": ind_id, "category": category, "name": name, "missing": missing}
                )
                continue

            fetch_fn, required_env_var = registry_module.get_fetcher(ind["source"])

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

            mapped = [
                {
                    "period": sheet_layout.map_to_grain_column(
                        r["period"], ind["frequency"], tab_grain
                    ),
                    "value": r["value"],
                }
                for r in raw_results
            ]
            fresh_by_indicator[ind_id] = mapped

            row_num = sheet_layout.assign_row(
                {"rows": existing_rows}, ind_id, running_max_row, header_row
            )
            running_max_row = max(running_max_row, row_num)
            row_by_indicator[ind_id] = row_num
            is_new_row_by_indicator[ind_id] = ind_id not in existing_rows

            succeeded += 1
            print(f"[OK] {ind_id}")

        if not fresh_by_indicator:
            # Nothing succeeded in this category this run -- nothing to
            # report in sheet_updates (failures/pending already recorded).
            continue

        all_periods = set(existing_periods)
        for periods in fresh_by_indicator.values():
            all_periods.update(p["period"] for p in periods)

        columns, dropped = sheet_layout.sliding_window(
            list(all_periods), tab_grain, retain_periods_by_frequency
        )
        kept_set = set(columns)
        col_index_by_period = {period: idx + 2 for idx, period in enumerate(columns)}

        rows_out: dict = {}
        for ind in cat_indicators:
            ind_id = ind["id"]
            if ind_id not in fresh_by_indicator:
                continue
            name = ind.get("name", ind_id)
            existing_row_state = existing_rows.get(ind_id)
            diff = sheet_layout.diff_rows(existing_row_state, fresh_by_indicator[ind_id])
            cells = [
                {
                    "column": entry["period"],
                    "col_letter": sheet_layout.column_letter(col_index_by_period[entry["period"]]),
                    "value": entry["value"],
                }
                for entry in diff
                if entry["period"] in kept_set
            ]
            cells.sort(key=lambda c: col_index_by_period[c["column"]])
            rows_out[ind_id] = {
                "row": row_by_indicator[ind_id],
                "label": name,
                "is_new_row": is_new_row_by_indicator[ind_id],
                "cells": cells,
            }

        sheet_updates[category] = {
            "header_row": header_row,
            "label_column": sheet_layout.column_letter(1),
            "columns": columns,
            "rows": rows_out,
            "drop_columns": dropped,
        }

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
        "sheet_updates": sheet_updates,
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
