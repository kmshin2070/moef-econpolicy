"""The ONLY module in this codebase allowed to read env var *values*.

Every other module may check whether a name is present in os.environ
(that's fine -- it never exposes the value), but only `get_key()` here
may return an actual secret value, and its return value must be passed
straight into an HTTP request call -- never printed, logged, or put into
an f-string that reaches stdout / an exception message / the output JSON.

`mask()` is the other half of the contract: every exception message, URL,
or response snippet that could contain a key must be run through mask()
before it is allowed to reach stdout, the output JSON, or the summary.
"""

from __future__ import annotations

import os
import re

# Matches env var *names* that hold sensitive material: API keys
# (BOK_API_KEY, FRED_API_KEY, ...), bare *_KEY vars (SUPABASE_KEY), and
# *_URL vars (SUPABASE_URL) -- broadened generically by naming convention
# rather than a hardcoded name list, so any future *_KEY/*_API_KEY/*_URL
# env var is covered automatically.
SENSITIVE_ENV_VAR_PATTERN = re.compile(r".*_(API_)?KEY$|.*_URL$")

# Common "key in a query string" param names, case-insensitive, used by the
# public APIs this project talks to (ECOS, KOSIS, data.go.kr, FRED, ...).
_KEY_PARAM_PATTERN = re.compile(
    r"(?i)\b(key|apikey|api_key|servicekey|authkey)=[^&\s]+"
)


def discover_required_env_vars(indicators: list[dict], registry: dict) -> set[str]:
    """Return the distinct env var NAMES required by the sources actually
    used in `indicators`, by asking each source's fetcher module for its
    REQUIRED_ENV_VAR. Does not read any values.

    `registry` maps source name -> fetcher module (as in fetchers.REGISTRY).
    Unknown sources are silently skipped here -- that validation happens
    separately in main.py so it can report unknown-source errors clearly.
    """
    sources = {ind.get("source") for ind in indicators if ind.get("source")}
    required: set[str] = set()
    for source in sources:
        module = registry.get(source)
        if module is None:
            continue
        var_name = getattr(module, "REQUIRED_ENV_VAR", None)
        if var_name:
            required.add(var_name)
    return required


def check_env_vars_present(var_names) -> dict[str, bool]:
    """Return {name: True/False} for whether each name is set in the
    environment. Only ever checks membership -- never reads or returns
    the value itself."""
    return {name: (name in os.environ) for name in var_names}


def get_key(var_name: str) -> str:
    """The only function in this codebase that returns an env var's actual
    secret value. Callers must pass the result straight into an HTTP
    request call -- never print/log/format it into a message."""
    return os.environ[var_name]


def _currently_set_sensitive_values() -> list[str]:
    """Internal helper: values (not names) of every currently-set env var
    whose name matches SENSITIVE_ENV_VAR_PATTERN, filtered to len>=4 so we
    don't accidentally mask trivial substrings. Used only inside mask()."""
    values = []
    for name, value in os.environ.items():
        if SENSITIVE_ENV_VAR_PATTERN.match(name) and value and len(value) >= 4:
            values.append(value)
    return values


def mask(text: str) -> str:
    """Redact secret material from `text` before it is allowed to reach
    stdout, the output JSON, or the summary.

    1) Any currently-set env var whose name matches SENSITIVE_ENV_VAR_PATTERN
       (any *_API_KEY, bare *_KEY like SUPABASE_KEY, or *_URL like
       SUPABASE_URL): if its value (len>=4) appears verbatim in `text`,
       replace with '***MASKED***'.
    2) Regex-strip common "key in query string" params case-insensitively:
       (key|apikey|api_key|serviceKey|authkey)=<value> -> same param name
       followed by =***MASKED***
    """
    if not text:
        return text

    masked = text
    for value in _currently_set_sensitive_values():
        if value and value in masked:
            masked = masked.replace(value, "***MASKED***")

    def _replace_param(match: "re.Match[str]") -> str:
        return f"{match.group(1)}=***MASKED***"

    masked = _KEY_PARAM_PATTERN.sub(_replace_param, masked)
    return masked
