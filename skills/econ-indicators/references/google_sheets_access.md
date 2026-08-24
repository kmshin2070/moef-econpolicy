# Google Sheets layout & access pattern

The `econ-indicators` scripts never call the Google Sheets API directly —
they have no Google credentials. All reads/writes go through the Routine's
Sheets connector, using `main.py`'s JSON input/output as the contract. This
document explains the sheet layout and how row/column positions are
computed, since `indicators.yaml`'s `sheet_range` field is **not** used at
runtime (see below).

## Tab layout

One tab per `category` value in `indicators.yaml` (15 tabs). Within a tab:
- **Column A** — indicator label (`name` from `indicators.yaml`), rewritten
  every run so edits to `name` propagate automatically.
- **Columns B onward** — one column per time period, oldest → newest,
  left → right. Header row (`settings.header_row` in `indicators.yaml`,
  currently `1`) holds the period labels.
- **Each row** — one indicator's time series.

Period label format depends on the indicator's `frequency`:
| frequency | label format | example |
|---|---|---|
| monthly | `YYYY-MM` | `2024-06` |
| quarterly | `YYYYQn` | `2024Q2` |
| annual | `YYYY` | `2024` |

## Tab grain & the one mixed-frequency tab

A tab's "grain" is the **finest** frequency among its indicators
(precedence: monthly > quarterly > annual). Every column in the tab is at
that grain. Today, 14 of 15 tabs are frequency-uniform (all-monthly,
all-quarterly, or all-annual). **"Industrial Activity Trends" is mixed**:
two monthly indicators (`ind_prod_mom`, `ind_prod_qoq_from_monthly`) plus
one quarterly indicator (`ind_prod_qoq_from_quarterly`) — so that tab's
grain is monthly, and the quarterly row's periods are mapped onto monthly
columns by taking the **last month of the quarter** (`2024Q1` → `2024-03`).
The same rule (generalized: a coarser-frequency row maps to the *end*
period of its span at the tab's grain — quarter → last month, year →
December) applies automatically if a future tab ever mixes frequencies
again; `sheet_layout.map_to_grain_column()` implements this.

## Sliding window (retention)

`indicators.yaml`'s `settings.retain_periods_by_frequency` sets how many
grain-columns to keep: 10 annual, 40 quarterly, 120 monthly — all equal to
"latest 10 years" at that grain. Each run, the target column set is
`union(periods already in the sheet, periods freshly fetched)`, sorted
chronologically, truncated to the most recent N. Anything older is
reported in `drop_columns` for that tab in `main.py`'s output, for the
Sheets connector to delete.

## Row assignment

- If an indicator already has a row in the sheet (per the sheet-state input
  JSON passed to `main.py`), that row is reused — this is idempotent and
  self-healing against sheets that were manually reordered.
- A new indicator (or first-ever run) gets
  `max(existing rows in that tab, header_row) + 1`.

## Why `sheet_range` in `indicators.yaml` is unused

Column position is inherently dynamic (sliding window — this week's
rightmost column becomes next week's second-to-rightmost, etc.), so a
static A1-style range recorded once in `indicators.yaml` can't stay
correct across runs. `main.py` computes row and column live, every run,
from the sheet-state input plus the rules above. The `sheet_range` field
is left in the YAML file untouched (per "don't invent or edit indicator
definitions") but is never read by any script.

## Input/output JSON contract

**Sheet-state input** (what the Sheets connector reads from the live sheet
before invoking `main.py`), keyed by tab (= category) then indicator id:
```json
{
  "tabs": {
    "GDP Growth Rate": {
      "periods": ["2016Q3", "2016Q4"],
      "rows": {
        "gdp_yoy": { "row": 2, "values": { "2016Q3": 2.1, "2016Q4": 2.3 } }
      }
    }
  }
}
```
A missing or empty file is treated as an empty state (first-run bootstrap),
not an error.

**Output** (what `main.py` writes for the Sheets connector to apply):
```json
{
  "run_metadata": {"timestamp": "...", "total": 38, "succeeded": 30, "failed": 2, "pending_configuration": 6},
  "sheet_updates": {
    "<category>": {
      "header_row": 1,
      "label_column": "A",
      "columns": ["2024-05", "2024-06"],
      "rows": {
        "<indicator_id>": {
          "row": 2,
          "label": "<name from indicators.yaml>",
          "is_new_row": false,
          "cells": [{"column": "2024-06", "col_letter": "C", "value": 3.4}]
        }
      },
      "drop_columns": ["2016-05"]
    }
  },
  "failures": [{"id": "kospi", "category": "Stock Price", "name": "...", "error": "<masked, no keys/full URLs>"}],
  "pending_configuration": [{"id": "employment_rate", "category": "Employment", "name": "...", "missing": ["series_id"]}],
  "summary_ko": "이번 주 경제지표 업데이트 결과: ..."
}
```
`cells` is a **minimal diff** — only new or changed values (float tolerance
`1e-9`) — so the connector writes as few cells as possible. `columns` is
always the tab's full target header, so the connector can reconcile it
cheaply regardless of what changed. `col_letter` is precomputed
(standard base-26 spreadsheet column letters) so the connector doesn't
need to do that arithmetic itself.

Three result buckets, not two: a real fetch failure (`failures`) never
blocks other indicators; an indicator whose `series_id`/`org_id` is still
`"TODO"` in `indicators.yaml` is never attempted and is reported separately
(`pending_configuration`) rather than counted as a failure.
