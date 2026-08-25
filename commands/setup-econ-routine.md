---
description: Guide a teammate through setting up their own econ-indicators Routine
---

# /setup-econ-routine

Each teammate runs their own Routine, under their own account, with their
own env vars and Supabase project — this command walks through that
setup. Do the steps below in order; ask the user for anything you can't
determine yourself (repo URL, Supabase project, which API keys they
hold).

## 1. Install the plugin (if not already)

```
/plugin marketplace add <this repo's URL or local path>
/plugin install moef-econpolicy@our-team-marketplace
```
(A cloned repo does not auto-load as a plugin just by being cloned — this
explicit install step is required even inside a Routine's environment.)

## 2. Create the Supabase table

In your (or the team's) Supabase project, open the SQL editor and run
`skills/econ-indicators/supabase_schema.sql` once — this creates the
`economic_indicators` table the script writes to. Do this before setting
any env vars below.

## 3. Set `SUPABASE_URL` and `SUPABASE_KEY`

From your Supabase project's Settings → API page, copy the project URL
(`SUPABASE_URL`) and the **service_role** key (`SUPABASE_KEY`), and set
both as env vars on the Routine's cloud environment (claude.ai/code →
cloud icon → edit environment → `.env`-format var list).

**`SUPABASE_KEY` (service_role) bypasses Row Level Security** — it is more
sensitive than any of the `*_API_KEY` values below and must be treated
accordingly: never paste it into chat, never share it outside the
Routine's environment, and never use it anywhere other than this Routine.
Note also that environment variables are visible to anyone using that
cloud environment (no secrets store today) — do not share this
environment with people outside the team.

## 4. Find out which API keys are needed, and set them

From a local checkout of this repo:
```
python skills/econ-indicators/scripts/main.py --list-required-keys
```
This prints the full list of env var **names** the current setup needs —
`SUPABASE_URL` and `SUPABASE_KEY` (always required) plus whichever
`*_API_KEY` names the current `indicators.yaml` needs (e.g. `BOK_API_KEY`,
`KOSIS_API_KEY`, `CUSTOMS_API_KEY`, `KRX_API_KEY`, `FRED_API_KEY` — the
exact fetcher-key list depends on what sources are in use; never assume a
fixed list, always re-run this after `indicators.yaml` changes). For each
`*_API_KEY` name printed:
- Help the user obtain their own key from that source's API portal (BOK
  ECOS, KOSIS, data.go.kr, KRX-hosted data.go.kr service, FRED).
- Add it to the same Routine environment as `SUPABASE_URL`/`SUPABASE_KEY`.
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
skill: update the economic indicators data and report a Korean summary."
Attach this repo as the Routine's repository so the plugin and
`indicators.yaml` are available at run time.

## 7. Test run

Trigger a manual run before relying on the schedule. Verify:
- The `economic_indicators` table in Supabase's Table Editor has rows for
  the ~34 fully-configured indicators.
- The chat-facing summary is in Korean and matches what's in the table.
- No API key value, Supabase key value, or full request URL appears
  anywhere in the run output.
- Any `pending_configuration` or `failures` entries make sense (e.g.
  indicators still marked `"TODO"` in `indicators.yaml` are expected to be
  pending until their codes are filled in and verified).

To view results as a spreadsheet: Supabase project → Table Editor →
`economic_indicators` → Export to CSV → open in Excel.
