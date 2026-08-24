"""Shared exception types for the econ-indicators backend.

Kept dependency-free (no imports from other project modules) so every
other module can import from here without risk of circular imports.
"""


class FetchError(Exception):
    """Raised by a fetcher module when a live data fetch fails.

    The message MUST already be passed through secrets.mask() by the
    raiser before this exception is constructed -- this module does not
    do any masking itself.
    """


class UnknownSourceError(Exception):
    """Raised when an indicator's `source` has no matching fetcher module
    registered in fetchers.REGISTRY."""


class ConfigError(Exception):
    """Raised for startup/config problems: missing env vars, malformed
    indicators.yaml, missing required fields, etc."""
