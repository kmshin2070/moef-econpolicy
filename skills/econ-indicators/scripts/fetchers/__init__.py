"""Real fetcher registry -- used by main.py unless --dry-run is passed
(in which case tests/fixtures/mock_fetchers.py is used instead, with the
same REGISTRY / get_fetcher shape)."""

from __future__ import annotations

from errors import UnknownSourceError

from . import bok_ecos, kosis, customs, krx, fred

REGISTRY = {
    "bok_ecos": bok_ecos,
    "kosis": kosis,
    "customs": customs,
    "krx": krx,
    "fred": fred,
}


def get_fetcher(source_name: str):
    module = REGISTRY.get(source_name)
    if module is None:
        raise UnknownSourceError(source_name)
    return module.fetch, module.REQUIRED_ENV_VAR
