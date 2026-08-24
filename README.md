# moef-econpolicy

A Claude Code plugin with two skills:

1. **`econ-indicators`** — keeps a Google Sheet updated weekly with ~38
   Korean/global economic indicators (latest 10 years, sliding window),
   pulled from BOK ECOS, KOSIS, data.go.kr customs, KRX, and FRED. Runs
   unattended inside a Claude Code **Routine** (cloud-scheduled) — each
   teammate runs their own, under their own account.
2. **`moef-ppt`** — generates MOEF-styled presentations (HTML preview +
   editable PPTX) from a script and design system. Copied in unchanged
   from the author's personal skill; see [Known limitation](#known-limitation-moef-ppt-portability)
   below.

## Install

This repo is both the plugin and a single-plugin marketplace pointing at
itself:
```
/plugin marketplace add <this repo's URL or local path>
/plugin install moef-econpolicy@our-team-marketplace
```
A cloned repo does **not** auto-load as a plugin just by being cloned —
run the two commands above explicitly, including inside a Routine's
environment.

## Layout

```
moef-econpolicy/
├── .claude-plugin/          # plugin.json, marketplace.json
├── skills/
│   ├── econ-indicators/     # Google Sheet indicator tracker
│   └── moef-ppt/            # MOEF presentation generator (copied, unchanged)
└── commands/
    └── setup-econ-routine.md
```

## Setting up your own Routine

Run `/setup-econ-routine` and follow the prompts — it walks through
installing the plugin, connecting a Google Sheets MCP connector, setting
`GOOGLE_SHEET_ID` and the required `*_API_KEY` vars, setting the weekly
schedule, and a test run.

## Adding an indicator

Add an entry to `skills/econ-indicators/indicators.yaml` under the right
`category` (creates a new row in that category's tab automatically). No
code changes needed as long as its `source` already has a registered
fetcher.

## Adding a data source

1. Create `skills/econ-indicators/scripts/fetchers/<name>.py` implementing
   `fetch(indicator, api_key)` and a module-level `REQUIRED_ENV_VAR`
   constant (e.g. `"NEWSOURCE_API_KEY"`).
2. Register it in `scripts/fetchers/__init__.py`'s `REGISTRY` dict.
3. Add indicators using `source: <name>` to `indicators.yaml`.

`main.py` and the security rules never need to change — key discovery and
masking are generic over any `*_API_KEY`-shaped env var, not a hardcoded
list.

## Security

- API keys are read only from env vars at runtime, via a single function
  (`scripts/secrets.py:get_key`) — never hardcoded, never written to a
  file, never printed/logged. Presence is checked by name only.
- All error messages, URLs, and the final run summary are passed through
  `secrets.mask()` before they can reach stdout or the output JSON,
  scrubbing any currently-set `*_API_KEY` value and common key query
  params (`key=`, `apikey=`, `serviceKey=`, ...) found in the text.
- No code dumps the full environment.
- `.gitignore` excludes `.env`, `*.env`, and other local secret files.
- Routine environment variables are visible to anyone using that cloud
  environment (no secrets store today) — don't share it outside the team.

## Data source research status

`indicators.yaml`'s `series_id`/`org_id` codes were filled in by researching
each source's official docs (see inline YAML comments for the exact
provenance/confidence per entry). **34 of 42 indicators are fully
configured** (mostly BOK ECOS, high-confidence, several live-verified
against ECOS's public sample key during research). **8 remain `"TODO"`**
and are skipped at runtime (reported under `pending_configuration`, never
attempted) rather than fabricated:
- All 6 `customs` (Export Trends: trade balance, exports, imports, auto/
  semiconductor/shipbuilding YoY) — data.go.kr's exact operation path
  couldn't be confirmed (spec behind an unfetchable Swagger/xlsx), and the
  3 item-level ones are additionally blocked by a June 2026 MTI
  classification overhaul that invalidated the legacy codes found. See
  `scripts/fetchers/customs.py`'s module docstring.
- Both `kosis` Government Debt indicators — not found as a discrete KOSIS
  series; the stronger lead (기획재정부 열린재정 openfiscaldata.go.kr) is a
  different source type, not pursued without a decision to add it.

Even the 34 filled-in entries are marked "verify before first run" in
`indicators.yaml` — several BOK ECOS tables (exchange rate, treasury
yields) are daily-only and get reduced to month-end client-side, which
should be double-checked against the intended convention.

## Known limitation: moef-ppt portability

`skills/moef-ppt/SKILL.md` was copied unchanged, per the original request.
It hardcodes absolute Windows paths to resources that live **outside**
this plugin (on the original author's machine): `pptxgenjs`/`jszip` under
an `IR_ppt\node_modules\` folder, Pretendard font files, a design-system
`.txt`, and two reference-implementation project folders. Copying this
plugin alone will not make `moef-ppt` work for a teammate who doesn't have
those same paths available — ask the plugin author if you need this skill
to run on a different machine.

## Requirement confirmation

- ✅ **API key security** — verified independently: ran
  `python -m compileall`, the full test suite (34/34 passing), a
  `--dry-run` against the real `indicators.yaml`, and the missing-env-var
  hard-abort path; grepped the whole `scripts/` tree confirming every
  `print(` call carries only names/ids/counts or an already-`mask()`-ed
  message, and that `os.environ` access is confined to `scripts/secrets.py`
  (plus its own test). No hardcoded key-like strings found anywhere in the
  repo. See [Security](#security).
- ✅ **Language split** — verified: all code, comments, `SKILL.md`,
  command docs, and this README are English; only the Google Sheet
  content and the chat-facing `summary_ko` are Korean.
