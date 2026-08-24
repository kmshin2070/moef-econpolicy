---
name: econ-indicators
description: >
  Keeps a Google Sheet updated with Korean/global economic indicators
  (latest 10 years, oldest period dropped as new ones arrive), pulled
  weekly from statistics APIs (BOK ECOS, KOSIS, data.go.kr customs,
  KRX, FRED). Designed to run unattended inside a Claude Code Routine.

  Use this skill whenever the user:
  - Asks to update the economic indicators sheet
  - Runs this as a scheduled Routine (see commands/setup-econ-routine.md)
  - Asks to add a new indicator or a new data source to econ-indicators
---

# econ-indicators

Fetches ~38 economic indicators from 5 statistics APIs, diffs them against
the current Google Sheet, and reports a Korean-language summary. The
Python script (`scripts/main.py`) only fetches and diffs — it never
touches Google Sheets directly (no Google credentials). Reading and
writing the sheet is done by you, the agent, via a connected Google
Sheets MCP connector (search the [Claude Directory](https://claude.ai/directory)
for "Google Sheets" if none is connected yet — see
`../../commands/setup-econ-routine.md`).

## Prerequisites

- `GOOGLE_SHEET_ID` env var set (the target spreadsheet).
- One `*_API_KEY` env var per data source actually used in
  `indicators.yaml`. To see exactly which ones are required, run:
  ```
  python scripts/main.py --list-required-keys
  ```
  This prints only var **names** — never run anything that dumps full
  environment variable values.

## Procedure

1. **Read the current sheet state.** Using the Google Sheets connector,
   read every tab (one tab per indicator `category` — see
   `references/google_sheets_access.md` for the full layout). Build a JSON
   file matching the schema in that reference doc (`{"tabs": {...}}`) and
   save it to a scratch path, e.g. `sheet_state.json`. If this is the very
   first run and the sheet has no tabs yet, pass an empty/missing file —
   the script treats that as a bootstrap case, not an error.

2. **Run the script:**
   ```
   python scripts/main.py --sheet-state-in sheet_state.json --output-out result.json
   ```
   Never let real API key values or the full output JSON appear in chat —
   only the short `[OK]`/`[FAIL]`/`[SKIP]` progress lines the script prints
   to stdout are safe to surface, and even those carry no sensitive data.

3. **Read `result.json`** and apply it via the Sheets connector:
   - For each tab in `sheet_updates`: write the full `columns` header row,
     write each row's `cells` (already a minimal diff — new/changed values
     only), and delete any columns listed in `drop_columns` (retention:
     latest 10 years per `settings.retain_periods_by_frequency`).
   - Create a new row (using the given `row` number and `label`) if
     `is_new_row` is true.

4. **Report the result to the user**, in Korean, using `result.json`'s
   `summary_ko` field as the basis — mention counts of succeeded/failed/
   pending-configuration indicators. If `failures` or `pending_configuration`
   is non-empty, briefly list which indicator ids and why (the `error`
   field is already safe to show — it never contains a raw key or full
   request URL).

## Notes

- One indicator's failure never blocks the others — `main.py` always
  finishes and reports a per-indicator breakdown.
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
