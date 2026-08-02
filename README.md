# WC2026 Format Evaluation

> **Work in progress.** This README describes the project as it stands
> today, not a finished deliverable. The final, polished README (with a
> reproducible headline claim a stranger can verify from a clean clone) is
> explicitly scoped as the project's last build — see `docs/build_plan.md`,
> Build C. Until then, treat this as an honest snapshot, not a pitch.

Evaluates whether FIFA's expansion of the World Cup to 48 teams increased
global representation without materially degrading competitive balance or
scheduling fairness, relative to prior tournament formats.

## What it does

Builds a Snowflake data pipeline for the 2026 FIFA World Cup: ingests
match results, stage/group structure, and venue data from independently
sourced and cited inputs; validates the data with automated, re-runnable
checks; models it into a dimensional schema; derives a travel/rest mart
from it; extends the same fact table with a historical comparison baseline
(2022, 1994); and sources each of those three tournaments' own FIFA World
Ranking. The 5 analytical marts that answer the core question — competitive
balance, group difficulty, upset rate, confederation performance, and
expected-vs-actual performance — are built, each with a hypothesis test
behind it (`docs/statistical_validation_results.md`) reporting an effect
size and practical significance alongside its p-value, never a causal
claim.

## Status

| Build | What it covers | State |
| --- | --- | --- |
| 0 | Feasibility research, source validation | Done |
| 1 | Problem statement, schema design | Done |
| 2 | Raw ingestion into Snowflake (`RAW` schema) | Done |
| 3 | Data-quality validation layer (`VALIDATION` schema) | Done |
| 4 | Dimensional model (`CORE` schema) | Done |
| 5 | Historical comparison layer (2022, 1994 alongside 2026; `ANALYTICS.TOURNAMENT_FORMAT_COMPARISON`) | Done |
| 7 | Venue coordinates + travel/rest mart (`ANALYTICS.TEAM_TRAVEL_REST`) | Done, second-source coordinate cross-check complete (issue #13) |
| 6 (part 1 of 2) | FIFA ranking sourcing + `CORE.TEAM_TOURNAMENT_RANKING`, mart metric definitions | Done (issue #19) |
| 6 (part 2 of 2) | 5 analytical marts + statistical validation layer (`docs/statistical_validation_results.md`) | Done (issue #23) |
| 8, 9, 10, C | Incremental-load demo, cross-account sharing, Power BI layer, consolidation | Not started |

Full build-by-build detail: `docs/build_plan.md`. Sourcing decisions and
their rationale: `docs/decision_log.md`.

## Architecture

Five Snowflake schemas, in dependency order:

```text
RAW          landed source files, as ingested, no transformation
VALIDATION   data-quality checks, rejected records, quality summary
CORE         dimensional model: dim_date, dim_group, dim_stage, dim_venue,
             dim_confederation, dim_team, dim_tournament, fact_match,
             team_tournament_ranking
ANALYTICS    marts built on CORE: TEAM_TRAVEL_REST, TOURNAMENT_FORMAT_COMPARISON,
             COMPETITIVE_BALANCE, GROUP_DIFFICULTY, UPSET_RATE,
             CONFEDERATION_PERFORMANCE, EXPECTED_VS_ACTUAL, and
             STATISTICAL_VALIDATION (one row per hypothesis test)
AUDIT        load metadata: rows loaded, warehouse, duration
```

`fact_match` is grain one-row-per-match: 104 rows for the 2026 tournament
plus 116 historical comparison rows (2022, 1994), 220 total, spanning the
3 tournaments in `dim_tournament`. `team_tournament_ranking` holds each
team's FIFA World Ranking per tournament (grain: team × tournament, since
a returning team's ranking differs by tournament — not a `dim_team`
column). Full schema diagram and column-level detail: `docs/architecture.md`.

## Setup

**Prerequisites**: Python 3 (developed against 3.14), a Snowflake account.

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Create a `.env` file in the repo root (never committed — already in
`.gitignore`) with:

```text
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_ROLE=
SNOWFLAKE_WAREHOUSE=
SNOWFLAKE_DATABASE=
SNOWFLAKE_SCHEMA=
```

`config.py` reads these via `python-dotenv`; every script in `src/`
imports from `config.py` rather than hardcoding credentials or file
paths.

## Usage

Run from the repo root, in order (each step is idempotent — safe to
re-run):

```bash
python -m src.ingestion.fetch_historical_results  # fetch the full historical results dataset (not committed)
python -m src.ingestion.setup_snowflake   # create schemas, tables, warehouse config
python -m src.ingestion.load_raw          # load all RAW source files
python -m src.core.build_core             # populate CORE dimensions + fact_match
python -m src.geospatial.build_travel_rest  # populate the travel/rest mart
python -m src.analytics.run_statistical_validation  # run hypothesis tests, populate ANALYTICS.STATISTICAL_VALIDATION
python -m src.validation.run_checks       # run data-quality checks
python -m src.validation.reconcile_counts # source-to-warehouse row count reconciliation
```

Run the test suite:

```bash
pytest tests/ -v
```

## Project structure

```text
config.py               Snowflake connection config + source file paths (env-driven)
data/
  raw/                   Source files, as pulled or independently compiled/cited
  processed/             Derived, reproducible outputs (e.g. the validated stage mapping)
docs/                    Problem statement, architecture, decision log, build plan,
                         data dictionary, mart metric definitions
sql/
  raw/                    RAW schema + table DDL, numbered for run order
  validation/             VALIDATION schema DDL + per-check detection queries
  core/                   CORE schema DDL + populate/ queries (dims, fact_match)
  analytics/               ANALYTICS schema DDL + populate/ queries (marts)
  audit/                    AUDIT schema DDL
src/
  ingestion/               Snowflake connection, schema setup, RAW loading
  validation/               Data-quality checks (Python + orchestration)
  core/                     CORE dimensional model population
  geospatial/                Travel/rest mart population
  analytics/                 Statistical validation layer (5 marts are plain SQL views)
  transform/                 Local, Snowflake-independent match/stage transform
tests/                    pytest suite + fixtures (including a deliberately bad-row fixture)
```

## Data sources

- **Match results**: `martj42/international_results` (CC0-licensed,
  historically maintained). See `docs/data_feasibility_report.md`, Source 1.
  Also the source for Build 5's historical comparison tournaments (2022,
  1994) — see `docs/decision_log.md`.
- **Stage/group draw**: Yahoo Sports editorial coverage, manually
  transcribed into `data/raw/wc2026_group_draw.csv`. Single-sourced,
  pending a second independent cross-check.
- **Team-to-confederation crosswalk**: compiled from known 2026
  qualifying outcomes, not scraped — no confederation data existed in any
  source found during feasibility research. See `docs/decision_log.md`.
- **Venue coordinates**: independently sourced and cited per venue from
  Wikipedia (`data/raw/wc2026_venue_coordinates.csv`), replacing an
  unlicensed, partially-fabricated third-party dataset ruled out during
  feasibility research. Cross-checked against a second independent source
  (OpenStreetMap/Nominatim, issue #13).
- **FIFA World Ranking**: one snapshot per tournament (2026, 2022, 1994),
  each from that tournament's own Wikipedia seeding/qualification article
  citing FIFA's own official ranking release
  (`data/raw/wc_fifa_ranking_snapshots.csv`). Several GitHub scraper repos
  and a third-party Elo-rating alternative were evaluated and rejected
  (no license, or not FIFA's own ranking system) — see
  `docs/decision_log.md`. Single-sourced, pending a second independent
  cross-check, same caveat status as the group draw and confederation
  crosswalk.

Every sourcing decision, including what was rejected and why, is logged
in `docs/decision_log.md`.
