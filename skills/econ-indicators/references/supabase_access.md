# Supabase table layout & access pattern

The `econ-indicators` scripts talk to Supabase's PostgREST API directly
(`supabase_client.py`), using its own `SUPABASE_URL`/`SUPABASE_KEY`
credentials — there is no connector and no separate apply step. This
document explains the table schema and the two REST call patterns
(`upsert_rows`, `delete_before`) `main.py` uses every run.

## Schema

One flat table, `economic_indicators`, one row per (indicator, period).
See `../supabase_schema.sql` for the exact DDL to run once in the
Supabase SQL editor:

```sql
create table economic_indicators (
  indicator_id   text not null,
  category       text not null,
  name_ko        text not null,
  period         text not null,
  frequency      text not null,
  value          numeric not null,
  unit           text not null,
  source         text not null,       -- bok_ecos | kosis | customs | krx | fred
  updated_at     timestamptz not null default now(),
  primary key (indicator_id, period)
);
```

Period label format depends on the indicator's `frequency` (same
convention as before, produced by `periods.format_period`):
| frequency | label format | example |
|---|---|---|
| monthly | `YYYY-MM` | `2024-06` |
| quarterly | `YYYYQn` | `2024Q2` |
| annual | `YYYY` | `2024` |

The primary key is `(indicator_id, period)` — every run's upsert targets
exactly this key pair, so re-running against the same period always
updates the existing row rather than duplicating it.

## Upsert pattern

Each run, per indicator, `main.py` POSTs the kept rows (post-retention-
window) in one call:

```
POST {SUPABASE_URL}/rest/v1/economic_indicators?on_conflict=indicator_id,period
apikey: <SUPABASE_KEY>
Authorization: Bearer <SUPABASE_KEY>
Content-Type: application/json
Prefer: resolution=merge-duplicates

[{"indicator_id": "gdp_yoy", "category": "...", "name_ko": "...",
  "period": "2024Q2", "frequency": "quarterly", "value": 3.7,
  "unit": "%", "source": "bok_ecos", "updated_at": "2024-08-05T00:00:00Z"}, ...]
```

`on_conflict=indicator_id,period` plus `Prefer: resolution=merge-duplicates`
is PostgREST's upsert idiom: a row whose (indicator_id, period) already
exists gets updated in place instead of erroring on the primary-key
constraint.

**`updated_at` must be set explicitly in the payload**, not left to the
column's `default now()`. That default only fires on a fresh `INSERT` —
on the conflict/update path PostgREST performs an `UPDATE`, which never
touches columns absent from the payload's default-application, so an
omitted `updated_at` would silently go stale on every re-run of an
already-existing period. `supabase_client.upsert_rows` sets it to the
current UTC timestamp on every call, for every row, unconditionally.

## Delete-by-cutoff (retention) pattern

After each indicator's upsert, `main.py` deletes anything now outside its
retention window:

```
DELETE {SUPABASE_URL}/rest/v1/economic_indicators?indicator_id=eq.<id>&period=lt.<cutoff>
apikey: <SUPABASE_KEY>
Authorization: Bearer <SUPABASE_KEY>
```

`cutoff` is the oldest period kept by that run's `periods.sliding_window`
call. `period=lt.<cutoff>` is a **lexicographic text comparison** — this
is safe because every period label this project produces is already
zero-padded (`YYYY-MM`, `YYYYQn`, `YYYY`), the same property
`periods.sliding_window` relies on for its own chronological sort. Text
ordering and chronological ordering coincide for these formats, so
PostgREST's plain `lt.` filter (no date casting needed) does the right
thing.

This delete step covers two cases: normal week-over-week retention
rollover (this run's window slid forward by one period), and any leftover
rows from before this migration or from a period when an indicator's
upstream history was wider than the currently configured retention.

## Auth & key sensitivity

Both calls use the same two headers:
- `apikey: <SUPABASE_KEY>`
- `Authorization: Bearer <SUPABASE_KEY>`

`SUPABASE_KEY` is expected to be the project's **service_role** key (see
`../../../commands/setup-econ-routine.md`). Unlike the anon/public key,
service_role **bypasses Row Level Security** entirely — treat it as more
sensitive than any of the `*_API_KEY` values this skill also uses, never
share it outside the Routine's own environment, and never use it in any
client-facing context. `scripts/secrets.py`'s masking pattern covers both
`SUPABASE_KEY` and `SUPABASE_URL` by naming convention (any `*_KEY`/
`*_URL`-suffixed env var), the same as it always covered `*_API_KEY`.
