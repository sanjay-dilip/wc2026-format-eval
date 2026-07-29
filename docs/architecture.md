# Architecture — 2026 World Cup Format Evaluation

Status: Build 1. Schema *shape* only (names, grain, dimension list). Nothing
below is implemented in Snowflake yet — that starts at Build 2. See
`docs/problem_statement.md` for the question this architecture serves.

---

## Schema names (locked)

| Schema       | Purpose                                                                 |
| ------------ | ------------------------------------------------------------------------ |
| `RAW`        | Landed source files, as ingested, no transformation                    |
| `VALIDATION` | Validation checks, rejected-records table, data-quality summary        |
| `CORE`       | Dimensional model — `dim_*` and `fact_match`, validated data only       |
| `ANALYTICS`  | Marts built on `CORE` (Build 6 onward): competitive balance, group difficulty, upset rate, confederation performance, expected-vs-actual |
| `AUDIT`      | Load metadata — rows loaded, warehouse used, duration, credits         |

`SHARED` is dropped from the original list. It only has a reason to exist if
Build 9 (cross-account sharing) is confirmed worth doing — that decision
hasn't been made, so the schema isn't created on spec. If Build 9 goes
ahead, it gets added then, with its own justification, not inherited from
this document.

---

## Dimensional model

Grain: `fact_match` is one row per match. 104 rows for the 2026 tournament
(Build 0's validated count); historical tournaments added in Build 5 extend
the same grain, not a different one.

```text
                        dim_date
                            |
                            |
  dim_venue --- fact_match --- dim_stage
                 |match_id (PK)|
                 |date_id (FK) |
                 |stage_id(FK) |
                 |venue_id(FK) |
                 |home_team_id-+---> dim_team ---> dim_group
                 |away_team_id-+---> dim_team ---> dim_confederation
                 |home_score   |
                 |away_score   |
                 |went_to_et   |
                 |went_to_so   |
                 |so_winner_id-+---> dim_team (nullable)
                 |neutral_site |
```

| Table              | Key fields (beyond PK)                                                        | Notes                                                                 |
| ------------------ | ------------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| `dim_team`          | `team_name` (canonical spelling), `group_id` (FK), `confederation_id` (FK), `fifa_ranking` | `fifa_ranking` nullable until Build 6 closes the rankings gap — not a placeholder guess |
| `dim_group`         | `group_letter`                                                                | 12 groups, 2026-specific; sourced from `data/raw/wc2026_group_draw.csv` |
| `dim_stage`         | `stage_name`, `stage_order`, `date_window_start`, `date_window_end`           | Group Stage, R32, R16, QF, SF, 3rd Place, Final — from Build 0's validated stage mapping |
| `dim_venue`         | `venue_name`, `city`, `country`, `latitude`, `longitude`                      | Lat/long carried as `NULL` until Build 7's independent re-verification — not copied from the unlicensed source (`docs/decision_log.md`) |
| `dim_confederation` | `confederation_name`                                                          | AFC, CAF, CONCACAF, CONMEBOL, OFC, UEFA                                |
| `dim_date`          | `full_date`, `year`, `month`, `day`, `day_of_week`                            | Standard date dimension, not 2026-specific — supports Build 5 historical comparison |
| `fact_match`        | see diagram                                                                   | `went_to_et` / `went_to_so` flags and nullable `so_winner_id` carry the FT-vs-ET-vs-shootout distinction documented in the feasibility report, rather than collapsing it into a single score field |

Foreign keys: `fact_match.date_id → dim_date`, `.stage_id → dim_stage`,
`.venue_id → dim_venue`, `.home_team_id` / `.away_team_id` / `.so_winner_id
→ dim_team`. `dim_team.group_id → dim_group`, `dim_team.confederation_id →
dim_confederation`.

This is schema *shape* only — column types, constraints, and the actual
`CREATE TABLE` statements are Build 2/4 work, not this one.

---

## Snowflake feature decisions (5-question test)

Test applied to each candidate from the original list: what problem does it
solve, why not something simpler, what does it cost, how is it
demonstrated, how is it tested. Anything that fails is cut here, on paper,
rather than built and rationalized afterward.

### Kept

| Feature | Why it survives |
| --- | --- |
| Internal stages | Real ingestion mechanism for the CSV files Build 0 already validated (match subset, shootouts). No simpler path to get files into Snowflake. |
| `COPY INTO` | The actual load mechanism Build 2 uses. Directly demonstrated by `RAW.MATCH` reaching exactly 104 rows; tested by re-running against the same files and confirming an identical, idempotent count. |
| File formats | Paired with `COPY INTO` to parse the CSVs correctly (delimiters, headers). Low cost, no simpler substitute once `COPY INTO` is in scope. |
| Streams | Detects new-match-arrival and correction events for Build 8's incremental-load demonstration. This is the actual change-detection mechanism, not a nice-to-have. |
| Tasks | Orchestrates the Stream-detected changes into `CORE` for Build 8. Demonstrated by the incremental-vs-full-refresh comparison test that build already requires. |
| Time Travel | Costs nothing extra to enable (no object to build, no ongoing spend) and ties directly to Build 3's deliberate bad-row injection test — recovering the pre-bad-row state via `AT`/`BEFORE` is a real, demonstrable use, not a token feature. |
| Zero-copy cloning | Build 4 already flags this as "revisit at that point, don't assume." Kept provisionally for that reason — not re-decided here, deferred on purpose per the build plan's own instruction. |
| Role-based access control | Directly demonstrates the `RAW`/`VALIDATION`/`CORE`/`ANALYTICS`/`AUDIT` schema separation with real access boundaries (e.g., an ingestion role that can't read `ANALYTICS`). Native feature, no extra infrastructure cost. Tested by attempting a cross-role query and confirming denial. |
| Account Usage views | Answers Build C's cost-report requirement (warehouse credits, query duration) with a real query against `WAREHOUSE_METERING_HISTORY`, not a manually kept tally. "Warehouse cost analysis" from the original list is this same mechanism, not a separate feature. |
| Resource monitors | Directly protects the actual stated constraint — the build plan notes primary-account credits expire soon. Cheap to configure, real operational relevance, not decorative. |

### Cut

| Feature | One-line reason |
| --- | --- |
| Raw JSON ingestion using `VARIANT` | No JSON-shaped source exists anywhere in this project — every Build 0 source is flat CSV. Would be added purely to check a resume-keyword box, not to solve a real ingestion problem. |
| Dynamic Tables | Redundant with the Streams + Tasks pattern already required for Build 8's incremental-load demo — keeping both would model the same "detect and act on change" concept twice for no added teaching value. |
| Query profiling | The core dataset is 104 rows. Nothing at that volume runs slowly enough to produce a real profiling story — would be a token screenshot, not a genuine optimization case. Revisit only if Build 5's full historical Jürisoo join (thousands of rows since 1872) turns out to need it. |

### Gated to a later build's own go/no-go (not pre-decided here)

| Feature | Gated to | Why not decided now |
| --- | --- | --- |
| Secure views | Build 9 | Only has a real security boundary to demonstrate if there's an actual second consumer account, per Build 9's own conditional scope. |
| Secure Data Sharing | Build 9 | This *is* Build 9. The build plan already requires a written go/no-go before starting it; not duplicated here. |
| Geospatial functions | Build 7 | Contingent on venue coordinates actually being independently re-verified first (open blocker #3) — no verified coordinates yet means nothing real to compute distances from. |
