---
name: econ-indicators
description: >
  Keeps a Supabase table updated with Korean/global economic indicators
  (latest 10 years, oldest period dropped as new ones arrive), pulled
  weekly from statistics APIs (BOK ECOS, KOSIS, data.go.kr customs, KRX,
  FRED). Designed to run unattended inside a Claude Code Routine.

  Use this skill whenever the user:
  - Asks to update the economic indicators data
  - Runs this as a scheduled Routine (see commands/setup-econ-routine.md)
  - Asks to add a new indicator or a new data source to econ-indicators
---

# econ-indicators

Fetches ~42 economic indicators from 5 statistics APIs and upserts them
straight into a Supabase table (`economic_indicators`), then reports a
Korean-language summary. The Python script (`scripts/main.py`) does the
whole job itself — fetch, retention-window trim, and write — via
Supabase's REST API (PostgREST), with its own Supabase credentials (no
connector, no human-in-the-loop write step).

## Prerequisites

- `SUPABASE_URL` and `SUPABASE_KEY` env vars set (the target Supabase
  project's REST endpoint and API key — see
  `references/supabase_access.md`). These are unconditionally required;
  Supabase is the one fixed storage backend, unlike fetcher sources.
- One `*_API_KEY` env var per data source actually used in
  `indicators.yaml`. To see exactly which env vars (Supabase's plus every
  active source's) are required, run:
  ```
  python scripts/main.py --list-required-keys
  ```
  This prints only var **names** — never run anything that dumps full
  environment variable values.

## Procedure

1. **Run the script:**
   ```
   python scripts/main.py --output-out result.json
   ```
   The script handles fetch, retention trimming, and the Supabase write
   itself — there is no separate apply/write step and nothing else for you
   to do to persist the data. Never let real API key or Supabase key
   values, or the full output JSON, appear in chat — only the short
   `[OK]`/`[FAIL]`/`[SKIP]`/`[DONE]` progress lines the script prints to
   stdout are safe to surface, and even those carry no sensitive data.

2. **Read `result.json`.**

3. **Report the result to the user**, in Korean, using `result.json`'s
   `summary_ko` field as the basis — mention counts of succeeded/failed/
   pending-configuration indicators. If `failures` or `pending_configuration`
   is non-empty, briefly list which indicator ids and why (the `error`
   field is already safe to show — it never contains a raw key or full
   request URL).

## Notes

- One indicator's failure never blocks the others — `main.py` always
  finishes and reports a per-indicator breakdown. A fetch that succeeds
  but whose Supabase write then fails is still reported under `failures`,
  not silently counted as a success.
- An indicator whose `series_id`/`org_id` is still `"TODO"` in
  `indicators.yaml` is skipped and reported under `pending_configuration`,
  not attempted.
- Adding a new indicator: add an entry to `indicators.yaml` under its
  `category` — no code changes needed as long as its `source` already has
  a registered fetcher.
- Adding a new source: add `scripts/fetchers/<name>.py` implementing
  `fetch(indicator, api_key)` and `REQUIRED_ENV_VAR`, then register it in
  `scripts/fetchers/__init__.py`'s `REGISTRY` dict. `main.py` itself never
  needs to change. See `scripts/fetchers/bok_ecos.py` for the pattern.
  (Sources stay pluggable this way — only the storage backend, Supabase,
  is a single fixed dependency.)
