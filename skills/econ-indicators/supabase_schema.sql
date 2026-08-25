-- economic_indicators table for the econ-indicators skill.
-- One-time DDL: run this once in your Supabase project's SQL editor
-- (Table Editor -> SQL Editor -> New query) before the first scheduled
-- run. Not executed by any script in this repo.

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
