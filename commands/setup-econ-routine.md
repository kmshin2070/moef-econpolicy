---
description: Guide a teammate through setting up their own econ-indicators Routine
---

# /setup-econ-routine

Each teammate runs their own Routine, under their own account, with their
own env vars and Sheets connection — this command walks through that
setup. Do the steps below in order; ask the user for anything you can't
determine yourself (repo URL, sheet ID, which API keys they hold).

## 1. Install the plugin (if not already)

```
/plugin marketplace add <this repo's URL or local path>
/plugin install moef-econpolicy@our-team-marketplace
```
(A cloned repo does not auto-load as a plugin just by being cloned — this
explicit install step is required even inside a Routine's environment.)

## 2. Connect a Google Sheets MCP connector

Claude Code has no single named built-in "Google Sheets connector" — it
depends on what's connected to the user's account. Ask the user:
- Do you already have a Google Sheets MCP connector connected (check
  claude.ai → Settings → Connectors, or the [Claude Directory](https://claude.ai/directory))?
- If not, help them find and connect one there before continuing.

When creating the Routine, make sure this connector is included in the
Routine's connector list (new Routines include all currently-connected
connectors by default — remove ones this Routine doesn't need, keep the
Sheets one).

## 3. Set `GOOGLE_SHEET_ID`

Create or pick the target spreadsheet, copy its ID from the URL
(`https://docs.google.com/spreadsheets/d/<THIS PART>/edit`), and set it as
an env var on the Routine's cloud environment (claude.ai/code → cloud icon
→ edit environment → `.env`-format var list). Note: environment variables
are visible to anyone using that environment (no secrets store today) — do
not share this environment with people outside the team.

## 4. Find out which API keys are needed, and set them

From a local checkout of this repo:
```
python skills/econ-indicators/scripts/main.py --list-required-keys
```
This prints only the env var **names** the current `indicators.yaml`
actually needs (e.g. `BOK_API_KEY`, `KOSIS_API_KEY`, `CUSTOMS_API_KEY`,
`KRX_API_KEY`, `FRED_API_KEY` — the exact list depends on what sources are
in use; never assume a fixed list, always re-run this after
`indicators.yaml` changes). For each name printed:
- Help the user obtain their own key from that source's API portal (BOK
  ECOS, KOSIS, data.go.kr, KRX-hosted data.go.kr service, FRED).
- Add it to the same Routine environment as `GOOGLE_SHEET_ID`.
- Never ask the user to paste the key value into chat, and never echo it
  back once entered.

## 5. Set the schedule

Weekly, Monday morning KST. In the Routine's schedule setting, pick the
weekly preset and set the time in your local zone (Claude Code converts
to UTC automatically) — e.g. Monday 09:00 KST. Custom cron (via
`/schedule update` in the CLI) is only needed if the weekly preset's day/
time options don't line up with Monday morning KST.

## 6. Set the Routine's prompt

Point it at the `econ-indicators` skill, e.g.: "Run the econ-indicators
skill: update the economic indicators Google Sheet and report a Korean
summary." Attach this repo as the Routine's repository so the plugin and
`indicators.yaml` are available at run time.

## 7. Test run

Trigger a manual run before relying on the schedule. Verify:
- All 15 tabs get created/updated as expected.
- The chat-facing summary is in Korean and matches what's in the sheet.
- No API key value or full request URL appears anywhere in the run output.
- Any `pending_configuration` or `failures` entries make sense (e.g.
  indicators still marked `"TODO"` in `indicators.yaml` are expected to be
  pending until their codes are filled in and verified).
