"""Fake fetcher registry used by `main.py --dry-run`. Same REGISTRY /
get_fetcher shape as fetchers/__init__.py, but returns deterministic fake
data with no network access and no env vars required.

Every REQUIRED_ENV_VAR here is a name that is never actually read (dry
run never calls secrets.get_key for these), so --dry-run works with zero
API keys configured.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from errors import UnknownSourceError  # noqa: E402


class _MockModule:
    def __init__(self, source_name: str):
        self.REQUIRED_ENV_VAR = f"MOCK_{source_name.upper()}_API_KEY"
        self._source_name = source_name

    def fetch(self, indicator: dict, api_key: str) -> list[dict]:
        """Deterministic fake series: 3 periods of made-up values, derived
        from the indicator id so different indicators get different (but
        stable across runs) numbers."""
        frequency = indicator.get("frequency", "monthly")
        indicator_id = indicator.get("id", "unknown")
        base_value = (sum(ord(c) for c in indicator_id) % 50) + 1.0

        if frequency == "monthly":
            periods = ["2024-04", "2024-05", "2024-06"]
        elif frequency == "quarterly":
            periods = ["2023Q3", "2023Q4", "2024Q1"]
        elif frequency == "annual":
            periods = ["2022", "2023", "2024"]
        else:
            periods = ["2024-06"]

        return [
            {"period": p, "value": round(base_value + i * 0.1, 2)}
            for i, p in enumerate(periods)
        ]


REGISTRY = {
    name: _MockModule(name)
    for name in ("bok_ecos", "kosis", "customs", "krx", "fred")
}


def get_fetcher(source_name: str):
    module = REGISTRY.get(source_name)
    if module is None:
        raise UnknownSourceError(source_name)
    return module.fetch, module.REQUIRED_ENV_VAR
