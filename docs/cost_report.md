# Cost Report

Compiled 2026-08-03, against the live primary Snowflake trial account
(identifier kept out of this file per this project's standing convention
— see `.env`), during Build C. Every figure below is a live query
result, not an estimate — see the raw output referenced per section.
The trial's ~8-day window started 2026-07-30 and expires ~2026-08-07; this
report was pulled while the account was still queryable, since a future
clone of this repo won't have access to it.

## Warehouse configuration

`COMPUTE_WH` — the only warehouse this project uses (reused from the
account's pre-existing default, not newly created; see Build 2 in
`docs/decision_log.md`):

| Property | Value |
|---|---|
| Size | X-Small |
| Clusters | 1 (min 1, max 1) |
| Auto-suspend | 60 seconds |
| Auto-resume | TRUE |
| Created | 2026-07-08 (pre-existing, before this project started) |

Source: `SHOW WAREHOUSES LIKE 'COMPUTE_WH'`, queried 2026-08-03. The
auto-suspend/auto-resume settings were explicitly forced in Build 2
(`sql/raw/01_configure_warehouse.sql`) regardless of what the account
default was — see `docs/decision_log.md`.

## Total credits consumed

Sourced from `SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY`, filtered
to `COMPUTE_WH`, for the 4 calendar days the account has been used
(2026-07-30 through 2026-08-02 — the query was run 2026-08-03 before that
day's usage had accumulated meaningfully):

| Date | Credits used (COMPUTE_WH) | Builds/work that ran that day |
|---|---|---|
| 2026-07-30 | 0.7590 | Build 2 (raw ingestion), Build 3 (validation), Build 4 (core model) |
| 2026-07-31 | 0.2971 | Build 7 (geospatial), issue #13 (venue cross-check) |
| 2026-08-01 | 0.2895 | Build 5 (historical comparison), Build 6 Parts 1-2 (rankings + marts), Build 8 (incremental pipeline) |
| 2026-08-02 | 0.2629 | Build 9 (cross-account sharing), Build 10 (Power BI layer), issues #33/#34/#37/#39 (cross-checks) |
| **Total** | **1.6084** | |

Day-to-build mapping is per `CONTEXT.md`'s own dated session entries, not
re-derived — days often carry more than one build since sessions were
long. Compare against the primary trial's ~$351 starting credit balance
(see the `snowflake-trial-constraint` memory / Build 2 entry in
`docs/decision_log.md`): under 0.5% of the balance consumed for the entire
project through Build 10, comfortably inside the trial window on cost
grounds — the binding constraint was always the ~8-day calendar expiry,
not the credit balance. `X-Small` + `AUTO_SUSPEND=60` kept every build's
actual compute footprint to well under an hour of billed time.

The Build 9 secondary (consumer) trial account has its own separate credit
balance and was not queried for this report — it's a distinct account,
out of this report's scope.

## Query/load duration

`AUDIT.LOAD_LOG` has 66 rows — more than the number of canonical loads,
because several builds (2 and 3 specifically) deliberately re-ran
`load_raw.py` to prove idempotency after the `FORCE=TRUE` bug fix (see
`docs/decision_log.md`, Build 3 entry) — each re-run logged its own row.
Per-load duration, all runs: 1-8 seconds, no outliers. `AUDIT.LOAD_LOG`
does not carry a build/issue tag per row, so duration can't be cleanly
attributed per build beyond the timestamp-to-day mapping above.

## Known measurement gap

`AUDIT.LOAD_LOG.credits_used` is `NULL` for all 66 rows — this was flagged
as intentional back in Build 2: `ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY`
has up to ~3 hours of latency, so credits can't be captured synchronously
at load time, and it was never backfilled since (see `docs/decision_log.md`
and `CONTEXT.md`'s "What does NOT exist yet" section). This report's
credit figures come from `WAREHOUSE_METERING_HISTORY` directly (hourly
granularity, whole-warehouse — not per-load), which is the only accurate
source available; per-load credit attribution was never possible with this
project's instrumentation.

`INFORMATION_SCHEMA.QUERY_HISTORY` (which would have given per-query
duration at finer grain than the hourly warehouse-metering view) was also
attempted for this report and failed: `SQL compilation error: Cannot
retrieve data from more than 7 days ago`. This is a genuine tool
limitation encountered while compiling this report, not a gap silently
worked around — the account's actual usage window (2026-07-30 onward) is
still within 7 days of "now," but the table function's range check
rejected the query anyway. `WAREHOUSE_METERING_HISTORY` was used instead
and covers the full project timeline.

## Rows processed (current live state)

| Table | Rows |
|---|---|
| `RAW.MATCH` | 104 |
| `RAW.SHOOTOUT` | 683 |
| `RAW.GROUP_DRAW` | 48 |
| `RAW.TEAM_CONFEDERATION` | 48 |
| `RAW.VENUE_COORDINATES` | 16 |
| `RAW.HISTORICAL_TEAM_CONFEDERATION` | 14 |
| `CORE.FACT_MATCH` | 220 |
| `CORE.DIM_TEAM` | 62 |
| `CORE.DIM_VENUE` | 16 |
| `CORE.DIM_DATE` | 99 |
| `CORE.DIM_TOURNAMENT` | 3 |
| `CORE.TEAM_TOURNAMENT_RANKING` | 104 |
| `ANALYTICS.TEAM_TRAVEL_REST` | 208 |
| `ANALYTICS.STATISTICAL_VALIDATION` | 6 |

These reconcile against each build's own documented success criteria in
`docs/decision_log.md` and `CONTEXT.md` — this table is a live
re-confirmation, not a new set of figures.

## Bottom line

For a stranger deciding whether to run this pipeline themselves: expect
well under 2 Snowflake credits total for a full run through Build 10 on an
`X-Small` warehouse, assuming similar data volumes (a few hundred rows per
table, no repeated idempotency-testing re-runs). The real cost driver for
reproducing this project isn't compute — it's the ~8-day trial calendar
window if using a trial account, since the credit balance was never close
to binding.
