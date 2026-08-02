# Decision Log — 2026 World Cup Format Evaluation

## 2026-08-01 — Build 9: Secure Data Share implementation

**Decision**: `SHARED` (new schema, dropped from the original list until
this exact decision - see the go/no-go entry below) holds 8 `SECURE
VIEW`s, each a thin `SELECT * FROM ANALYTICS.<object>` wrapper
(`sql/shared/01_create_secure_views.sql`). `WC2026_SHARE`
(`sql/shared/02_create_share_and_grants.sql`) is granted `USAGE` on the
database and the `SHARED` schema, and `SELECT` on each of the 8 views
individually - `RAW`/`VALIDATION`/`CORE`/`ANALYTICS` are never granted to
the share directly, so the share's surface is exactly these 8 views.

**Real constraint found while writing the grants, not assumed**:
`GRANT SELECT ON ALL VIEWS IN SCHEMA WC2026.SHARED TO SHARE WC2026_SHARE`
fails outright - `Bulk grant on objects of type VIEW to SHARE is
restricted`, confirmed against the live account. Snowflake requires
per-view grants to a share; `FUTURE VIEWS` isn't a workaround either
(same restriction). Fixed by granting each of the 8 views by name.
Consequence, documented rather than silently true: adding a 9th shared
view later needs a 9th `GRANT` line in
`sql/shared/02_create_share_and_grants.sql`, not just a new
`CREATE VIEW`.

**`ALTER SHARE ... SET ACCOUNTS` needs the consumer's org-qualified
identifier** (`org_name.account_name`, e.g. `BFVUNPZ.KPB88773`) - not the
legacy account locator used to connect (`WOB90221`), and not something
stored in `.env` redundantly. `src/sharing/setup_share.py` looks this up
live via `CURRENT_ORGANIZATION_NAME()`/`CURRENT_ACCOUNT_NAME()` on the
secondary account each run, the same "derive at runtime instead of
storing a second copy" reasoning `config.py` already uses for
credentials. `SET ACCOUNTS` (not `ADD ACCOUNTS`) is used deliberately -
idempotent by construction, since re-running it always results in
exactly the one intended consumer rather than accumulating duplicates.

**The pre-existing `WC2026_CONSUMER` database on the secondary account
(created ahead of this build, alongside gathering its connection details)
is left untouched, not dropped or repurposed.** `CREATE DATABASE ... FROM
SHARE` creates its own new database object bound to the share
(`WC2026_FROM_SHARE`); reusing `WC2026_CONSUMER`'s name would have
required dropping it first, a destructive step this build doesn't
actually need. Confirmed empty (only `INFORMATION_SCHEMA`/`PUBLIC`)
before deciding this, not assumed safe to ignore.

**Both success criteria verified against the live account, not
assumed**, via `src/sharing/verify_consumer_access.py`:
- BI-shaped query against `WC2026_FROM_SHARE.SHARED.COMPETITIVE_BALANCE`
  succeeds and returns real rows (2026/2022/1994 competitive-balance
  figures).
- `SHOW SCHEMAS IN DATABASE WC2026_FROM_SHARE` lists exactly `SHARED` and
  `INFORMATION_SCHEMA` - nothing else is visible from the consumer side
  at all, not just access-denied on request.
- A direct `SELECT * FROM WC2026_FROM_SHARE.RAW.MATCH` is actually
  attempted (not assumed to fail) and fails with `Schema
  'WC2026_FROM_SHARE.RAW' does not exist or not authorized` - `RAW` isn't
  merely permission-denied, it's not even visible as a schema from the
  consumer account.

Both `setup_share.py` and `verify_consumer_access.py` were re-run a
second time end-to-end to confirm idempotency; both produced identical
results.

---

## 2026-08-01 — Build 9 go/no-go: GO, bounded scope

**Decision**: Build 9 (Cross-Account Sharing) goes ahead, scoped strictly
to what `docs/build_plan.md` already specifies - a Secure Data Share from
the primary account to the secondary trial account, plus the secure views
needed to expose it, plus a verified-not-assumed check that `RAW` is
inaccessible from the consumer side. Nothing broader.

**The 5-question test** (`docs/architecture.md`'s own method, applied here
rather than skipped):

- **What problem does it solve?** Demonstrates producer/consumer
  separation - a real Snowflake-specific capability (governed data
  distribution without copying or replicating data) that nothing else in
  this project shows. The `RAW`/`VALIDATION`/`CORE`/`ANALYTICS`/`AUDIT`
  schema split already demonstrates *internal* governance (RBAC gate, not
  yet built); this is the only build that demonstrates *external*
  governance - a second account getting curated access without ever
  seeing ingestion internals.
- **Why not something simpler?** A second `.env`-configured connection to
  the same account, or a plain cross-database query, wouldn't demonstrate
  account-level isolation at all - the entire point is that the consumer
  is a genuinely separate account with its own credentials, unable to see
  `RAW` even if it tried. Confirmed today: both accounts are independently
  reachable, `AWS_US_WEST_2` on both sides (verified live via
  `CURRENT_REGION()`, not assumed from memory) - so this doesn't need
  Snowflake's replication feature either, which would be new complexity
  this project has no other reason to touch.
- **What does it cost?** Negligible. Creating a share is a metadata
  operation, not a compute job. Consumer-side queries run against the
  secondary account's own `COMPUTE_WH` (already exists, confirmed today),
  not the primary's - no additional draw on the primary trial's credit
  balance beyond the few statements needed to create the share and secure
  views.
- **How is it demonstrated?** The build plan's own success criteria: the
  consumer account runs BI-shaped queries against the shared object(s)
  successfully, and a direct attempt to query `RAW` from the consumer
  account is actually attempted and confirmed to fail - not assumed
  hidden because it wasn't granted.
- **How is it tested?** Same pattern as every other build: a script run
  against both live accounts, output pasted, not described. Failure of
  the "`RAW` is inaccessible" check is the one result this build cannot
  silently pass through - if it can be queried, that's a real finding,
  not a footnote.

**Why now, not deferred again**: This build was previously flagged as
at-risk specifically because the second account didn't exist yet. That
blocker is gone - connection details were gathered and independently
verified today (both accounts on `AWS_US_WEST_2`, confirmed via live
`CURRENT_REGION()` query on each, not just the account-creation-time
memory). The project is also running ahead of schedule at this point, so
there's real slack to absorb this build without crowding out what's still
to come.

**Explicitly out of scope, so this doesn't grow past what earns its
complexity**: no new analytical marts on the consumer side (it queries
what the share exposes, nothing new is computed there), no attempt to
make the share bidirectional, no replication (not needed - same region),
no additional roles beyond what's needed to own/consume the share.

---

## 2026-08-01 — Build 8: incremental load via Streams + Tasks, compared by natural key not match_id

**Decision**: `RAW.MATCH_STREAM` (Stream on `RAW.MATCH`) feeds
`CORE.SP_APPLY_MATCH_STREAM()` (stored procedure, `sql/core/10_create_apply_match_stream_procedure.sql`),
which applies corrections (`METADATA$ISUPDATE = TRUE`) via `UPDATE` and
new matches (`METADATA$ISUPDATE = FALSE`) via `INSERT`, both keyed on
`CORE.FACT_MATCH`'s existing natural key (`tournament_id`, `date_id`,
`home_team_id`, `away_team_id`) - no truncate, unlike every other
`CORE` populate query in this project. `CORE.INCREMENTAL_FACT_MATCH_TASK`
wraps the procedure call, matching `docs/architecture.md`'s Streams+Tasks
commitment for this build.

**A real, load-bearing constraint found while designing this, not
glossed over**: `CORE.FACT_MATCH.match_id` is assigned by
`ROW_NUMBER() OVER (ORDER BY match_date, home_team, away_team)` at full-
rebuild time (`sql/core/populate/07_fact_match.sql`), then the historical
block is appended starting at `MAX(match_id) + 1`
(`sql/core/populate/10_fact_match_historical.sql`). Inserting one new 2026
match and then running a full rebuild shifts every historical row's
`match_id` up by 1, because the 2026 block now has 105 rows instead of
104, moving the historical block's starting offset. The incremental path
correctly leaves historical `match_id`s untouched (only `RAW.MATCH`
changed, not `RAW.HISTORICAL_MATCH`) and assigns the new row
`MAX(match_id) + 1` directly - which does **not** match what a full
rebuild produces for the historical block, even though every row's actual
match data is identical. **Consequence**: Build 8's "incremental result
equals full-refresh result, byte- or hash-identical" success criterion
(`docs/build_plan.md`) is verified by hashing `CORE.FACT_MATCH` joined
back to natural-key/business columns (team names, tournament year, match
date, scores, stage name, venue name - see
`src/incremental/demo_incremental_load.py`'s `FACT_MATCH_NATURAL_VIEW_QUERY`),
not by hashing raw `match_id`/`date_id`/etc. surrogate keys, which are
rebuild-order-dependent by design in this schema.

**A second, narrower constraint, also documented rather than assumed**:
the incremental `INSERT` branch's `MAX(match_id) + ROW_NUMBER()`
assignment only agrees with what a from-scratch rebuild's global
`ROW_NUMBER()` would produce when the new match's
`(match_date, home_team, away_team)` sort key is not earlier than every
existing 2026 row's - true for a genuinely new match arriving after the
tournament's last already-loaded date (exactly what "new-match arrival"
describes), not true in general for an arbitrary backdated insert. Out of
scope for this build; not silently assumed to hold universally.

**Demonstrated and verified against the live account, not assumed**:
`src/incremental/demo_incremental_load.py` runs 3 scenarios - new-match
arrival, a score correction, and an idempotent no-op rerun - each
comparing the incremental result against a full rebuild
(`src.core.build_core.main()`) by content hash, raising on any mismatch
(a real committed automated test per the build plan's success criterion,
not a one-time manual check). All 3 passed. The script also drives
`CORE.INCREMENTAL_FACT_MATCH_TASK` once via `EXECUTE TASK`, polling
`TASK_HISTORY` for `SUCCEEDED`, as a secondary confirmation that the Task
object itself works - the main correctness proof calls the procedure
directly instead, for deterministic synchronous timing. Cleans up back to
the original 220-row baseline afterward (same fixture-and-cleanup
discipline as Build 3's deliberately-injected bad-row test) and was
re-run twice end to end to confirm the whole demo, not just the
procedure, is safely re-runnable.

**Cost decision**: `CORE.INCREMENTAL_FACT_MATCH_TASK` is created with a
schedule (`60 MINUTE`, documenting what a production deployment would
use) but is never `RESUME`d - Snowflake creates tasks `SUSPENDED` by
default. A continuously scheduled task would poll the warehouse every
interval regardless of whether `RAW.MATCH_STREAM` has pending data, real
if small compute cost this project's trial-credit constraint doesn't need
to spend. The demo drives it with an explicit `EXECUTE TASK` on demand
instead.

**Real bug found and fixed while building this**:
`src/ingestion/setup_snowflake.py`'s `run_sql_file()` split each `.sql`
file's statements on a naive `.split(";")`, which breaks
`10_create_apply_match_stream_procedure.sql` - its `$$`-quoted procedure
body itself contains semicolons (`BEGIN TRANSACTION; ... COMMIT;`).
Fixed by switching to the Snowflake connector's own
`conn.execute_string()`, which parses statement boundaries the same way
Snowflake does (respecting dollar-quoting) instead of blindly splitting
on every `;`. Caught immediately by re-running `setup_snowflake.py`
end-to-end after adding the new file, before this was committed anywhere.

---

## 2026-08-01 — Build 6 Part 2: 5 ANALYTICS marts + statistical validation layer

**Decision**: All 5 marts from `docs/metric_definitions.md` are built as
`CREATE OR REPLACE VIEW`s (`sql/analytics/03`-`07`), not populated tables -
same choice Build 5 made for `ANALYTICS.TOURNAMENT_FORMAT_COMPARISON`.
Each is a plain `GROUP BY`/`JOIN` over `CORE.FACT_MATCH`,
`CORE.DIM_TEAM`, and `CORE.TEAM_TOURNAMENT_RANKING`, so it's always
current with no separate idempotency mechanism needed - unlike
`ANALYTICS.TEAM_TRAVEL_REST`, none of these 5 needed a self-join complex
enough to justify a populated table.

**Statistical validation layer**: `src/analytics/run_statistical_validation.py`
runs one hypothesis test per applicable metric, per
`docs/problem_statement.md`'s rule (hypothesis stated, assumption checked,
effect size + practical significance alongside any p-value,
"associated with"/"consistent with" language only):
- **Competitive Balance** - Mann-Whitney U, 2026 vs pooled 2022+1994 mean
  |goal difference|. Not statistically significant (p=0.397), negligible
  effect (rank-biserial r=-0.064).
- **Upset Rate** - Fisher's exact test, 2026 vs pooled 2022+1994 upset
  rate among decisive, ranking-eligible matches. Not statistically
  significant at alpha=0.05 (p=0.052), small effect (Cohen's h=-0.360) -
  2026's upset rate (11.1%) is directionally lower than pooled historical
  (24.7%).
- **Confederation Performance** - Kruskal-Wallis H, 2026-only, goal
  differential by confederation. Statistically significant (p=0.0009),
  medium effect (epsilon-squared=0.079) - does not identify which
  confederation(s) differ from which.
- **Expected-vs-Actual** - Spearman correlation, run once per tournament
  (fifa_ranking vs actual finish). All 3 significant, medium-to-large
  effects (rho -0.49 to -0.67, negative as expected since a lower ranking
  number is a stronger team).

Full results, including every assumption check performed, are in
`docs/statistical_validation_results.md` (generated by the script, not
hand-written) and `ANALYTICS.STATISTICAL_VALIDATION` (one row per test,
queryable independent of the doc).

**Real bug found and fixed while building this**: `docs/metric_definitions.md`
(Upset Rate, written in Part 1) stated 2022 and 1994 "both have 100%
ranking coverage." Live data disagreed - 2022 has 29/32 teams ranked, not
32/32 (3 intercontinental/UEFA playoff winners weren't yet known at the
2022 seeding snapshot date, same situation as 2026's 6 late qualifiers,
just smaller). `ANALYTICS.UPSET_RATE`'s `eligible_match_count` is computed
from the live `CORE.TEAM_TOURNAMENT_RANKING` data, not from this prose, so
it was already correct - only the doc was wrong. Corrected in
`docs/metric_definitions.md` with the real 42/48, 29/32, 24/24 split,
citing the Build 6 Part 1 sourcing entry below which had the right numbers
all along; the "100%" line was an error introduced when that entry's
findings were summarized into the metric definition, not a new sourcing
problem.

**Live validation performed, not assumed**: all 5 mart views queried
directly against the account after creation (row counts and spot-checked
values - see PR description for the actual output). `setup_snowflake.py`
re-run end-to-end after adding files 03-08 to confirm the new files don't
break dependency-safe re-run. `run_statistical_validation.py` run twice in
a row - identical 6 rows and identical statistics both times, same
idempotency check every other populate script in this project uses.

---

## 2026-07-31 — Build 6 Part 1: FIFA ranking sourcing, ingestion, and mart metric definitions

**Decision**: FIFA World Ranking data is sourced as **one snapshot per
tournament** (2026, 2022, 1994), each pulled from that tournament's own
Wikipedia seeding/qualification article, not a continuous historical
ranking time series. `data/raw/wc_fifa_ranking_snapshots.csv` (104 rows -
one per team per tournament) and `CORE.TEAM_TOURNAMENT_RANKING` (grain:
team x tournament, not a `dim_team` column) hold this.

**Why a snapshot per tournament, not a full historical dataset**: open
blocker #1 originally framed this as "resolve FIFA rankings sourcing" in
the abstract, but the actual need - per this build's own mart definitions
(`docs/metric_definitions.md`, written as part of this same issue) - is
narrower: upset rate and expected-vs-actual only need each team's ranking
*at the time of the tournament it played in*, not a month-by-month series
going back decades. Framing it this way turned an open-ended, hard sourcing
problem into a bounded, verifiable one.

**Candidates evaluated and rejected**:
- **FIFA's own ranking page** (`inside.fifa.com/fifa-world-ranking/men`) -
  confirmed directly (fetched and inspected): JS-rendered SPA, empty HTML
  shell, only column headers retrievable. Same conclusion the 2026-07-21
  decision-log entry already reached for FIFA's match-centre pages -
  consistent finding, not re-litigated from scratch.
- **`Dato-Futbol/fifa-ranking`** (GitHub, scraped historical FIFA rankings
  Dec 1992-Sept 2024) - confirmed via the GitHub API (`"license": null`):
  no LICENSE file. Same disqualifying reason as the mominullptr repo ruled
  out in Build 0 (`docs/data_feasibility_report.md`, Source 3) - default
  all-rights-reserved copyright, real reuse risk. Also stale (no 2026
  coverage).
- **`cnc8/fifa-world-ranking`** (GitHub, similar scraper) - also confirmed
  `"license": null` via the GitHub API. Same rejection reason.
- **eloratings.net** (World Football Elo Ratings, 1901-2026 coverage) -
  not FIFA's own ranking system (a different rating methodology), no
  documented API, requires headless-browser scraping (PhantomJS, per a
  project that consumes it) with no confirmed reuse terms found on the
  primary site itself on direct inspection. A linked Kaggle mirror exists
  but Kaggle pages are JS-rendered and couldn't be inspected for license
  terms without a Kaggle account/API token - would also have broken this
  project's established fetch-script pattern (plain unauthenticated HTTP
  GET, no credentials - `src/ingestion/fetch_historical_results.py`,
  Build 5).
- **`mominullptr/FIFA-World-Cup-2026-Dataset`** - already disqualified
  project-wide in Build 0 for confirmed fabricated data and no LICENSE
  file; a later self-reported "CC0" claim on the same project's own GitHub
  Pages site does not override that direct finding, especially given
  Build 0's own conclusion was "marketing claims do not match source code
  behavior" for this exact repo. Not reconsidered.

**Source used**: each tournament's own Wikipedia seeding/qualification
article, which cites FIFA's own official ranking release for that date as
its primary source - the same tier and reasoning already applied to venue
coordinates (`docs/decision_log.md`, Build 7 research entry: public,
officially-published facts, individually citable and checkable, not
disputed numbers). Raw wikitext was fetched directly (`action=raw`, not
AI-summarized page text) and parsed with a script to avoid transcription
error, given the volume (104 team/rank pairs across 3 pages):
- 2026: [`2026 FIFA World Cup draw`](https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_draw),
  ranking as of 19 November 2025 (FIFA's own release, cited in the
  article). 42 of 48 teams covered - the article states plainly the other
  6 were playoff winners not yet determined at the 5 December 2025 draw.
- 2022: [`2022 FIFA World Cup seeding`](https://en.wikipedia.org/wiki/2022_FIFA_World_Cup_seeding),
  ranking as of 31 March 2022. 29 of 32 teams covered - 3 were
  intercontinental/UEFA playoff winners not yet known at the 1 April 2022
  draw.
- 1994: [`1994 FIFA World Cup qualification`](https://en.wikipedia.org/wiki/1994_FIFA_World_Cup_qualification),
  ranking as of **19 November 1993** (not "June 1994" - an earlier
  AI-summarized read of this page got the date wrong, caught by checking
  the raw wikitext directly rather than trusting the summary; this is
  exactly why the raw-fetch approach was used for the actual data
  extraction). All 24 teams covered.

**Cross-checked, not assumed**: every parsed (team code, rank) pair was
mapped to this project's canonical team-name spellings and checked against
the exact team rosters already established for each tournament
(`wc2026_confederation_map.csv` for 2026, `wc_historical_matches.csv` for
2022/1994). The "missing" teams in each source (6 for 2026, 3 for 2022, 0
for 1994) matched **exactly** the teams each Wikipedia article itself says
weren't determined yet at that snapshot date - a real cross-check that
caught nothing wrong, which is itself the confirmation the parse and
mapping are correct, not just internally consistent.

**A genuine tie found, not smoothed over**: Argentina and Switzerland both
show FIFA ranking **9** in the 1994 snapshot. Not a parsing bug - both
values were independently re-verified against the raw wikitext rows.
Left as-is; an early-era FIFA ranking formula (the system was only ~2
months old at this snapshot date) producing an exact tie between two
teams is plausible and not this project's place to silently break.

**Design decision: rankings are a team x tournament bridge table, not a
`dim_team` column.** `docs/architecture.md`'s original Build 1-era design
put `fifa_ranking` directly on `dim_team`, written when only 2026 existed
and a single snapshot per team was sufficient. Build 5 changed that: a
returning team (e.g. Brazil, in all 3 comparison tournaments) has a
genuinely different ranking each time - confirmed live: Brazil is ranked
4th (1994), 1st (2022), and 5th (2026). A single `dim_team.fifa_ranking`
column cannot hold three different values for the same team, so it stays
permanently `NULL` (not populated as Build 1 originally planned - the
column is left in place, not dropped, since dropping it is outside this
change's scope). `CORE.TEAM_TOURNAMENT_RANKING` (grain: team x tournament)
is the actual source of truth going forward.

**Metric definitions**: all 5 Build 6 marts (competitive balance, group
difficulty, upset rate, confederation performance, expected-vs-actual)
have full written definitions - business meaning, formula, grain, null
handling, ET/shootout handling, historical comparability - in the new
`docs/metric_definitions.md`, written before any mart SQL exists, per this
build's own success criteria. Two of the five (group difficulty,
expected-vs-actual) are explicitly gated to partial or 2026-only coverage,
stated there rather than discovered later: group difficulty has no data
for 2022/1994 at all (no group source ever existed for those years -
Build 5), and expected-vs-actual can only use a real stage-level "actual
finish" for 2026, falling back to an explicitly-flawed match-count proxy
for 2022/1994.

**Why this is a compiled static CSV, not a fetch script like Build 5's**:
`data/raw/wc_fifa_ranking_snapshots.csv` is committed directly (like
`wc2026_venue_coordinates.csv` and `wc2026_confederation_map.csv`), not
regenerated on demand from a fetch script (like
`international_results_full.csv`, Build 5). The distinction is
deliberate: `international_results_full.csv` comes from a single
maintainer's versioned, append-only CSV file - safe to re-fetch anytime
and get the same historical rows back. Wikipedia articles are
live-edited, not versioned or append-only - re-running a "fetch and parse"
script months from now could silently return different numbers if the
article changed, invalidating this entry's cross-checks without anyone
noticing. A compiled, cited, one-time extraction (same pattern as the
2026-07-21 Yahoo Sports entry: "manually transcribed... not scraped
programmatically... a one-time historical reconstruction") is the
correct choice for a source that isn't stable to re-fetch, not a gap.

**Validation performed, against the live account, not assumed**:
`RAW.FIFA_RANKING_SNAPSHOT` = 104 rows. `CORE.TEAM_TOURNAMENT_RANKING` =
104 rows, 9 with `fifa_ranking IS NULL` (exactly the 6 + 3 teams not yet
determined at each tournament's snapshot date - confirmed, not assumed).
`CORE.DIM_TEAM.fifa_ranking` confirmed `NULL` for all 62 rows (superseded,
per above). Confirmed idempotent by running `src/core/build_core.py`
twice in a row with identical results. `src/geospatial/build_travel_rest.py`
and the full validation/test suite (16/16 pytest) re-run afterward with no
regressions - this change only added a table, it didn't touch anything
Build 5 built.

---

## 2026-07-31 — Build 5: Historical Comparison Layer

**Decision**: `CORE.FACT_MATCH` is extended with historical World Cup
matches from **2022 (32-team format)** and **1994 (24-team format)**,
alongside 2026 (48-team format) - same grain, one new `CORE.DIM_TOURNAMENT`
dimension, per `docs/architecture.md`'s original plan ("historical
tournaments added in Build 5 extend the same grain, not a different one").
Not "all of World Cup history" - two specific, deliberately chosen prior
tournaments, one per format era `docs/build_plan.md` names (32-team,
24-team), satisfying the "2-3 prior World Cups" success criteria without
open-ended scope.

**Why 2022 and 1994, not others**: Maximizes team-name overlap with the
already-validated 2026 confederation crosswalk (26/32 teams and 15/24
teams respectively already resolve via `wc2026_confederation_map.csv`),
minimizing new crosswalk entries needed while still covering two distinct
non-48-team formats. A third, older tournament (16-team era, e.g. 1970)
was considered and rejected for this pass: `build_plan.md`'s own wording
only names 32/24/48-team formats, and 1970 specifically was found (see
below) to have a data-quality issue worth flagging separately rather than
folding into this decision under time pressure.

**Fetch script gap closed**: `data/raw/international_results_full.csv` has
been gitignored since Build 0 with a comment expecting a fetch script -
none existed until now. `src/ingestion/fetch_historical_results.py` pulls
`results.csv` from `raw.githubusercontent.com/martj42/international_results`
directly, validates the header shape and a row-count floor (49,520, the
count confirmed at Build 0), and writes it to `data/raw/`. Verified by
deleting the local file and re-running the script from nothing:
`Wrote 49520 data rows to ...international_results_full.csv`. Before this,
`src/transform/build_stage_mapping.py` and `tests/test_stage_mapping.py`
silently depended on a manually-placed file with no way to regenerate it
on a fresh clone - a real reproducibility gap, not a hypothetical one.

**Team/confederation name standardization - checked, not assumed**:
Compared every team name in the 2022 and 1994 filtered match data against
`wc2026_confederation_map.csv`'s spellings directly (e.g. confirmed
"South Korea" is used consistently across both eras, not "Korea
Republic"). Zero spelling mismatches found for the 41 overlapping team
appearances. The 14 teams with no 2026 presence (Bolivia, Bulgaria,
Cameroon, Costa Rica, Denmark, Greece, Italy, Nigeria, Poland, Republic of
Ireland, Romania, Russia, Serbia, Wales) got a new crosswalk file,
`data/raw/wc_historical_confederation_map.csv`, compiled the same way as
Build 4's 2026 crosswalk (known, stable FIFA confederation membership, not
scraped) - checked exactly against the historical match data's team list:
zero missing, zero extra.

**A retroactive-naming issue was found and is why 1970 was excluded, not
silently worked around**: Directly inspecting 1970 World Cup rows in
`international_results_full.csv` showed the Soviet Union recorded as
`"Russia"` and West Germany recorded as `"Germany"` - the source dataset
appears to retroactively apply the modern successor state's name to some
historical political entities rather than the name that existed at the
time. Neither 2022 nor 1994 exhibits this (USSR dissolved in 1991,
Germany reunified in 1990 - both already used their real, current-at-the-
time names in those years' data). This is a genuine data-quality finding
about the source, not a bug in this project's code - flagged here rather
than silently trusted, and is the concrete reason a 16-team-era tournament
was left out of this pass rather than a scope-convenience excuse.

**Format differences - explicit, not glossed over**: Historical rows have
`stage_id = NULL` and `venue_id = NULL` in `CORE.FACT_MATCH` - no verified
stage/round-label source exists for 2022 or 1994 in this project (the
Yahoo Sports crosswalk Build 0 used is 2026-specific), and no
venue-coordinate research has been done for non-2026 stadiums (a separate,
much larger undertaking, out of scope here - parallel to Build 4's
`went_to_et`/`neutral_site` reasoning). `CORE.FACT_MATCH.stage_id` and
`.venue_id` were changed from `NOT NULL` to nullable to allow this
(`ALTER TABLE ... ALTER COLUMN ... DROP NOT NULL`), and the orphaned-FK
check in `src/core/build_core.py` was updated to only flag a NULL FK as
orphaned when the row's tournament requires it to be populated (2026 rows
still enforced, historical rows exempted on this basis alone - see that
file's `FACT_MATCH_FK_CHECKS`).
`dim_team.group_id` is also `NULL` for the 14 historical-only teams (no
2026 group applies to them) - the existing `LEFT JOIN` in
`06_dim_team.sql` already handled this correctly with no change needed.
`CORE.DIM_TOURNAMENT.team_count` is computed from `COUNT(DISTINCT team)`
against the actual loaded matches per tournament, not hardcoded, so it
can't silently drift from the data.

**The comparison metric itself**: `ANALYTICS.TOURNAMENT_FORMAT_COMPARISON`
(a view, not a populated table like `TEAM_TRAVEL_REST` - it's a plain
`GROUP BY` over `fact_match`, always current, no separate idempotency
mechanism needed) computes `match_count`, `avg_goals_per_match`,
`pct_one_goal_margin`, `pct_drawn_after_et`, and
`shootout_decided_matches` identically across all three tournaments -
deliberately restricted to metrics derivable from score columns alone, no
ranking baseline (Build 6, still gated on rankings sourcing) and no
stage/group breakdown (not populated for historical rows, per above).
Full metric definitions in the view's own SQL comment
(`sql/analytics/02_create_tournament_format_comparison_view.sql`).

**A real bug found and fixed along the way**: The first version of
`sql/core/populate/01_dim_date.sql` (extending `dim_date` to cover three
separate tournament date windows) used a plain comma cross join between
the 3-row tournament-range relation and `TABLE(GENERATOR(ROWCOUNT => 60))`.
Confirmed directly this does **not** re-run the generator per outer row in
Snowflake - `SEQ4()` came out round-robin-distributed across all 3 rows
instead of restarting at 0 for each one, producing dates strided by 3 and
silently dropping most of the intended range (`dim_date` landed at 32 rows
instead of the expected 99, and `fact_match`'s 2026 insert - which joins
through `dim_date` - dropped to 35 rows instead of 104). Fixed by
rewriting the generator join as a `LATERAL` subquery, which forces
per-row evaluation; verified by re-running and getting the expected 99
`dim_date` rows and 104+64+52=220 `fact_match` rows. See
`sql/core/populate/01_dim_date.sql`'s own comment for the mechanism.

**A second real bug found and fixed**: `ANALYTICS.TEAM_TRAVEL_REST`'s
`LAG()` window (`sql/analytics/populate/01_team_travel_rest.sql`) was
partitioned by `team_id` alone. Once `fact_match` held matches from three
tournaments, a team appearing in more than one (e.g. Brazil in 1994, 2022,
and 2026) got its "previous match" computed across tournament boundaries -
first run after this build's changes showed rows-with-no-previous-match
dropping from the expected 48 to 19, and rows-with-a-previous-match-but-
missing-distance/rest rising from the expected 0 to 29 (a previous match
from a different tournament has `venue_id = NULL`, per above, so no
distance is computable). Fixed by partitioning by `(team_id,
tournament_id)` instead. Re-ran and confirmed the exact Build 7 baseline
restored: 208 rows, 48 tournament-openers, 0 unexpected NULLs,
`distance_km` 0-4302.7 km, `rest_days` 3-8 - identical to Build 7's
original figures, confirming this mart's 2026 output is unchanged by
Build 5, just computed correctly now that other tournaments share the
fact table.

**Validation performed, against the live account, not assumed**:
`CORE.DIM_DATE` = 99 rows (39 for 2026 + 29 for 2022 + 31 for 1994, zero
overlap), `CORE.DIM_TEAM` = 62 rows (48 2026 teams + 14 historical-only,
zero teams with a NULL `confederation_id`, exactly 14 with a NULL
`group_id`), `CORE.DIM_TOURNAMENT` = 3 rows, `CORE.FACT_MATCH` = 220 rows
(104 + 64 + 52), 0 orphaned FKs on every checked column (`tournament_id`
included, `stage_id`/`venue_id` checked NULL-tolerantly). Confirmed
idempotent by running `src/core/build_core.py` twice in a row with
identical results both times.
`ANALYTICS.TOURNAMENT_FORMAT_COMPARISON` queried live:

| tournament_year | team_count | format_label | match_count | avg_goals_per_match | pct_one_goal_margin | pct_drawn_after_et | shootout_decided_matches |
|---|---|---|---|---|---|---|---|
| 1994 | 24 | 24-team | 52 | 2.71 | 46.2 | 21.2 | 3 |
| 2022 | 32 | 32-team | 64 | 2.69 | 37.5 | 23.4 | 5 |
| 2026 | 48 | 48-team | 104 | 2.96 | 33.7 | 23.1 | 4 |

Shootout counts (3 for 1994, 5 for 2022) were independently cross-checked
against `shootouts_full.csv` by hand for those years' actual World Cup
knockout matches (Bulgaria over Mexico, Sweden over Romania, Brazil over
Italy for 1994; Japan-Croatia, Morocco-Spain, Croatia-Brazil,
Netherlands-Argentina, and Argentina-France for 2022) and matched real
tournament history, not just internal consistency.

---

## 2026-07-31 — Issue #13: venue coordinates cross-checked against a second independent source

**Decision**: `data/raw/wc2026_venue_coordinates.csv` now carries a second,
independently-sourced coordinate per venue (`second_latitude`,
`second_longitude`, `second_source_url`) alongside the original
Wikipedia-sourced value, plus a computed `cross_check_distance_m` column —
the great-circle distance in meters between the two. `RAW.VENUE_COORDINATES`
was extended to match (4 new columns via `ALTER TABLE ... ADD COLUMN IF NOT
EXISTS`, not a drop/recreate, so `CREATE TABLE IF NOT EXISTS` still holds
for a fresh account) and reloaded.

**Second source used**: OpenStreetMap, queried via the Nominatim geocoding
API (`nominatim.openstreetmap.org/search`), one query per venue by stadium
name + city. OSM is independently useful here specifically because its
stadium-location data is community-surveyed/mapped, not derived from
Wikipedia's infobox coordinates — satisfies the issue's requirement of "not
another page that itself cites Wikipedia."

**Cross-check result**: All 16 venues agree with the original Wikipedia
value well inside the stated tolerance ("a few hundred meters is
expected/harmless"). Distances (haversine, computed locally, not eyeballed):

| City | Distance (m) |
|---|---|
| East Rutherford | 2.7 |
| Mexico City | 3.9 |
| Toronto | 4.1 |
| Vancouver | 5.3 |
| Guadalupe | 6.7 |
| Philadelphia | 8.9 |
| Arlington | 9.3 |
| Kansas City | 10.7 |
| Houston | 15.6 |
| Seattle | 16.6 |
| Miami Gardens | 17.9 |
| Foxborough | 19.0 |
| Zapopan | 22.7 |
| Santa Clara | 31.0 |
| Inglewood | 45.3 |
| Atlanta | 80.2 |

Largest disagreement (Atlanta, 80.2 m) is still two orders of magnitude
below the stated tolerance and is consistent with the two sources pinning
slightly different points on the same stadium footprint (e.g. center of
the building vs. a named entrance) — not a sourcing error. No venue
required a decision about resolving a larger disagreement; none arose.

**No CORE correction needed**: Since every original (Wikipedia) value is
confirmed accurate to within tens of meters, `CORE.DIM_VENUE`'s existing
lat/long values were left as-is — re-verified, not re-derived. Re-ran
`src/core/build_core.py` and `src/geospatial/build_travel_rest.py` anyway,
per the issue's explicit validation requirement, against the live account:
`CORE.DIM_VENUE` = 16 rows (unchanged), `fact_match` = 104 rows (unchanged),
0 orphaned FKs, `ANALYTICS.TEAM_TRAVEL_REST` = 208 rows with 48
no-previous-match rows and 0 rows with a previous match but a missing
distance/rest value — identical to Build 7's original figures, confirming
this cross-check didn't change the numbers, only their evidentiary
strength.

**Status update**: Open blocker #3 (venue coordinates) is now fully
resolved — independently sourced *and* independently cross-checked, no
longer single-sourced to Wikipedia. Group draw and confederation crosswalk
(blockers #2 and #5) remain single-sourced and unaffected by this issue,
per its explicit "not in scope" note.

---

## 2026-08-02 — Issue #33: group draw cross-checked against a second independent source

**Decision**: `data/raw/wc2026_group_draw.csv` now carries a second,
independently-sourced group assignment per team (`second_source_url`,
`cross_check_match`) alongside the original Yahoo Sports-sourced value.
`RAW.GROUP_DRAW` was extended to match (2 new columns via `ALTER TABLE ...
ADD COLUMN IF NOT EXISTS`, not a drop/recreate, same pattern issue #13 used
on `RAW.VENUE_COORDINATES`) and reloaded.

**Second source used**: Wikipedia's per-group articles
(`en.wikipedia.org/wiki/2026_FIFA_World_Cup_Group_A` through `..._Group_L`),
one article per group, fetched directly (not taken from a search-result
summary) for groups A, K, and L to confirm exact wording, with the
remaining 9 groups' team lists corroborated via FIFA.com's own draw-results
and per-group articles surfaced in the same research pass. Wikipedia is
independently useful here specifically because it is not the Yahoo Sports
article the original crosswalk came from, and its per-group pages cite
FIFA's own final draw (staged 2025-12-05 in Washington, DC) directly —
satisfies the issue's requirement of "not another page that itself cites
Yahoo Sports."

**Cross-check result**: All 12 groups (48 teams) agree with the original
Yahoo Sports-sourced assignment exactly — `cross_check_match = TRUE` on
every row, zero disagreements. One cosmetic name-form note, not a
disagreement: the second source's per-group pages use "Czech Republic"
(matching this project's already-canonical spelling per the 2026-07-21
decision log entry), not "Czechia."

**No CORE correction needed**: Since every original group assignment is
confirmed accurate, `CORE.DIM_GROUP`/`CORE.FACT_MATCH` required no changes.
Re-ran `src/transform/build_stage_mapping.py` and `src/core/build_core.py`
anyway, per the issue's explicit validation requirement, against the live
account: `wc2026_stage_mapping.csv` regenerated byte-for-byte identical (no
git diff), `fact_match` = 220 rows (unchanged, 104 2026 + 64 2022 + 52
1994), 0 orphaned FKs on every checked column — identical to the
pre-cross-check figures, confirming this cross-check didn't change the
data, only its evidentiary strength.

**Status update**: Open blocker #2 (group draw) is now fully resolved —
independently sourced *and* independently cross-checked, no longer
single-sourced to Yahoo Sports. Confederation crosswalk (blocker #5)
remains single-sourced and unaffected by this issue, tracked separately in
issue #34.

---

## 2026-08-02 — Issue #34: confederation crosswalk cross-checked against a second independent source

**Decision**: `data/raw/wc2026_confederation_map.csv` (48 2026 teams) and
`data/raw/wc_historical_confederation_map.csv` (14 incremental 1994/2022
teams) now carry a second, independently-sourced confederation membership
per team (`second_source_url`, `cross_check_match`) alongside the original
compiled-from-general-knowledge value (2026-07-30 "Team->confederation
crosswalk compiled, not scraped" entry). `RAW.TEAM_CONFEDERATION` and
`RAW.HISTORICAL_TEAM_CONFEDERATION` were both extended to match (2 new
columns via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, same pattern
issues #13 and #33 used) and reloaded.

**Second source used**: Wikipedia's own per-confederation membership
articles (`CONCACAF`, `CONMEBOL`, `Oceania_Football_Confederation`,
`Confederation_of_African_Football`, `Asian_Football_Confederation`,
`UEFA`) — six pages total, each fetched directly and cross-referenced
against every team tagged with that confederation in both crosswalk
files, rather than per-team pages. Independently useful here because the
original crosswalk cites no source at all (it was compiled, not scraped),
so any cited source raises the evidentiary bar; three teams whose
membership wasn't visible in an initial truncated page fetch (South Korea,
Uzbekistan — both AFC; Republic of Ireland — UEFA) were separately
confirmed via targeted search before being marked matched, not assumed
from list length alone.

**Cross-check result**: All 62 teams (48 in the 2026 crosswalk + 14
incremental historical teams) match their confederation-membership listing
on the corresponding Wikipedia confederation page exactly — zero
disagreements. Confederation membership is a discrete, slow-changing fact
(not a tolerance-banded measurement like venue coordinates), so this is a
binary match/no-match check, not a distance calculation.

**No CORE correction needed**: Since every original confederation
assignment is confirmed accurate, `CORE.DIM_CONFEDERATION`/
`CORE.DIM_TEAM.confederation_id` required no changes. Re-ran
`src/core/build_core.py` anyway, per the issue's explicit validation
requirement, against the live account: `DIM_CONFEDERATION` = 6 rows
(unchanged), `DIM_TEAM` = 62 rows (unchanged) with 0 rows having a NULL
`confederation_id`, `fact_match` = 220 rows (unchanged), 0 orphaned FKs on
every checked column — identical to the pre-cross-check figures,
confirming this cross-check didn't change the data, only its evidentiary
strength.

**Status update**: Open blocker #5 (confederation crosswalk) is now fully
resolved — independently sourced *and* independently cross-checked, no
longer resting on compiled-from-general-knowledge alone. All five original
open blockers from the feasibility phase are now closed except blocker #4
(tactical efficiency theme, still an undecided go/no-go, not a sourcing
gap).

---

## 2026-07-30 — Build 7: rest-day definition and time zone handling, decided before calculating

**Decision**: `rest_days` in the travel/rest mart is `DATEDIFF('day',
previous_match_date, match_date)` — full calendar days elapsed since a
team's previous match, computed on the bare `match_date` values already
in `RAW.MATCH`. No time zone conversion is applied anywhere in this
calculation.

**Why no time zone conversion**: `RAW.MATCH` (and every upstream source
feeding it) carries only a `match_date` — no kickoff time-of-day, no time
zone field. There is nothing to convert: time zone handling only matters
when comparing two clock times across zones, and no clock time exists
anywhere in this project's data. Converting a bare date across time zones
would be inventing precision the source data doesn't have, not correcting
an omission.

**What this simplification actually costs**: two teams with the same
`rest_days` value may have had meaningfully different real-world rest —
e.g. a team playing a 9pm ET kickoff followed by a 12pm PT kickoff three
calendar-days later rested closer to 3.5 days in wall-clock terms than a
team with two mid-afternoon local kickoffs three calendar-days apart.
This is stated plainly rather than glossed over, per the build plan's
explicit instruction to document time zone handling before any
calculation runs — not because a fix is being deferred, but because no
fix is possible without a data source this project doesn't have.

**Distance calculation**: uses Snowflake's native `ST_MAKEPOINT`/
`ST_DISTANCE` geography functions (great-circle distance between
consecutive venue coordinates, in km) — this is the "Geospatial
functions" feature `docs/architecture.md` already kept, explicitly
contingent on venue coordinates being independently re-verified first.
That happened in the previous decision-log entry; this is the build that
was gated on it.

**Validation performed**: Ran against the live account.
`ANALYTICS.TEAM_TRAVEL_REST` = 208 rows (104 matches × 2 teams), 48 rows
with no previous match (one per team, its tournament opener), 0 rows with
a previous match but a missing `distance_km`/`rest_days`. `distance_km`
ranges 0–4302.7 km (20 rows at exactly 0 km — teams playing consecutive
matches at the same venue), `rest_days` ranges 3–8 (mean ~5.3) — both
sane for this tournament's format. Spot-checked Argentina's full
8-match run to the Final: every `previous_match_date + rest_days =
match_date` held exactly. Confirmed idempotent by running
`src/geospatial/build_travel_rest.py` twice in a row with identical
results both times.

---

## 2026-07-30 — Build 7 research: venue coordinates independently sourced

**Decision**: `data/raw/wc2026_venue_coordinates.csv` (16 venues, one row
each) is the independently re-verified replacement for the venue
coordinates that were ruled out in Build 0's feasibility pass (open
blocker #3). Each row cites its own Wikipedia source URL — not copied
from the disqualified "FIFA-World-Cup-2026-Dataset" repo
(`docs/data_feasibility_report.md`, Source 3: no LICENSE file, confirmed
fabricated data elsewhere in the same repo).

**Why Wikipedia**: `docs/data_feasibility_report.md` characterizes venue
coordinates as "public facts, easily re-sourced" — this isn't a
disputed-numbers problem the way rankings or tactical stats are, it's a
sourcing-and-citation problem. Wikipedia's per-stadium infobox
coordinates are independently checkable (each cites its own primary
source in turn) and structurally distinct from the disqualified repo:
no licensing conflict (facts aren't copyrightable), no relation to that
repo's confirmed fabrication.

**Cross-checks performed**:
- The 16-stadium list itself was verified against Wikipedia's "2026 FIFA
  World Cup" venues section, independent of any per-stadium page.
- Every city name in the coordinates file was checked for exact string
  match against `RAW.MATCH`'s 16 normalized venue cities (after the
  Dallas→Arlington fix in PR #10) — zero missing, zero extra.
- Guadalupe (not Monterrey) and Zapopan (not Guadalajara) were confirmed
  directly from each stadium's own Wikipedia article, matching what
  `RAW.MATCH` already records — these are real suburb/city distinctions,
  not naming inconsistencies like Dallas/Arlington.

**At the time of this entry, not yet done**: A second independent source
per venue (the same standard the group draw and confederation crosswalk
are held to). Coordinates are precise enough for the intended use (travel
distance between consecutive venues) but each one is currently backed by
a single source. Loading these into `dim_venue` and building the
travel-distance mart is Build 7's implementation, done separately from
this research pass. Depended on PR #10 (Dallas/Arlington fix, merged
2026-07-30) so coordinates land on the correctly-deduped 16-row
`dim_venue`, not a 17-row table with a phantom duplicate. **Resolved
2026-07-31, issue #13** — see that entry above for the second-source
cross-check.

---

## 2026-07-30 — dim_venue double-counted Arlington/Dallas as separate venues

**Decision**: Normalize `venue_city = 'Dallas'` to `'Arlington'` in the
`CORE` population layer only (`sql/core/populate/05_dim_venue.sql` and the
`fact_match` join in `07_fact_match.sql`). `RAW.MATCH` is left untouched.

**Why**: Found while compiling the venue list for Build 7's coordinate
research. `RAW.MATCH` records 8 matches with `venue_city = 'Arlington'`
and 1 match (Portugal vs Spain, 2026-07-06) with `venue_city = 'Dallas'`
— but both are the same physical stadium, AT&T Stadium in Arlington, TX.
It was temporarily rebranded "Dallas Stadium" for World Cup broadcast
purposes (FIFA avoids sponsor-named stadium branding), and the upstream
Jürisoo source recorded that one match's city inconsistently. Confirmed
via CBS News and multiple ticketing sources (Gametime, SeatGeek,
Ticketmaster all list the match at "AT&T Stadium, Arlington, TX").
Before this fix, `CORE.DIM_VENUE` had 17 rows for what is really 16
distinct venues, and the Portugal-Spain match's `fact_match.venue_id`
pointed to a phantom duplicate venue instead of the real Arlington row.

**Why fix in CORE, not RAW**: `RAW` is documented as "landed source
files, as ingested, no transformation" (`docs/architecture.md`) — the
inconsistency is genuinely present in the source, so `RAW.MATCH` should
keep reflecting it faithfully. The correction belongs at the
transformation layer, same as every other RAW→CORE derivation.

**Validation performed**: Re-ran `src/core/build_core.py` after the fix;
`CORE.DIM_VENUE` = 16 rows (was 17), `fact_match` still 104 rows, 0
orphaned FKs on every checked column (same check as Build 4).

---

## 2026-07-30 — Build 4: zero-copy clone of CORE cut for the initial load

**Decision**: Do not zero-copy clone `CORE` before populating it for the
first time in Build 4.

**Why**: Build 1 kept zero-copy cloning provisionally, explicitly deferring
the cost/benefit call to Build 4 ("revisit at that point, don't assume it
still holds" — `docs/architecture.md`). The actual justification for
cloning is protection against a risky transformation mutating *existing*
valuable data. `CORE`'s tables are empty going into this build — there is
no prior state worth protecting, and Time Travel (already kept, per
`docs/architecture.md`) already gives a free rollback path for anything
that goes wrong during this session. Cloning empty tables adds no real
protection here.

**Revisit condition**: Once `CORE` holds validated data that a later build
would risk mutating (e.g. a schema change or backfill after Build 5/6),
re-apply the original justification then, not retroactively here.

---

## 2026-07-30 — Team→confederation crosswalk compiled, not scraped

**Decision**: `data/raw/wc2026_confederation_map.csv` (48 teams → 6 FIFA
confederations) is compiled directly from known 2026 World Cup qualifying
outcomes, not pulled from any external file or source in this repo — no
confederation data existed anywhere in the project before this.

**Why**: Unlike the venue-coordinate problem (Source 3, ruled out for
license and fabrication reasons), FIFA confederation membership by country
is stable, publicly known, and not the kind of fact that gets fabricated
or disputed between sources — there's no equivalent "unlicensed repo with
plausible-looking numbers" risk here. The compiled split (16 UEFA / 10 CAF
/ 9 AFC / 6 CONCACAF / 6 CONMEBOL / 1 OFC = 48) was checked against the
confirmed 48-team roster (`data/raw/wc2026_group_draw.csv`) for exact name
match — zero missing, zero extra.

**Residual risk, stated plainly**: A small number of teams reached the
tournament via intercontinental or confederation playoff routes (e.g.
Iraq, Jordan, DR Congo) rather than direct qualification. The confederation
assignment itself is not in question (playoff route doesn't change which
confederation a team belongs to), but this crosswalk has not been
cross-checked against a second independent source the way the group draw
was. Treat it the same way the group draw is treated pending its own
second cross-check: usable, not yet load-bearing in a published claim
without one.

---

## 2026-07-30 — Build 4: `went_to_et` and `neutral_site` left NULL in `fact_match`

**Decision**: `fact_match.went_to_et` and `fact_match.neutral_site` are
populated as `NULL` for all 104 rows in Build 4, not derived or guessed.

**Why**: `docs/data_dictionary.md` documents that `home_score`/`away_score`
in the Jürisoo source are already FT+ET combined, with no separate
regulation-time-only score field — so there is no way to tell, from data
currently in `RAW`, whether a given knockout match actually went to extra
time versus being decided in 90 minutes. Similarly, the upstream source
(`international_results_full.csv`) carries a `neutral` flag, but
`data/processed/wc2026_stage_mapping.csv` (the actual `RAW.MATCH` load
source) does not carry that column through — it was dropped when the
Build 0 transform was built, before this need was identified.
`went_to_so` *is* derivable (a shootout record for the match exists or it
doesn't) and is populated correctly.

**Revisit condition**: If `neutral_site` is needed later, extend
`src/transform/build_stage_mapping.py`'s output to carry the `neutral`
column through from `international_results_full.csv` (surgical change,
not now — that CSV is a validated, committed artifact, not touched as a
side effect of Build 4). `went_to_et` would need a genuinely new source
with regulation-time scores; none has been found in this project.

---

## 2026-07-21 — Match-results backbone: use martj42/international_results, not a 2026-specific dataset

**Decision**: The CC0-licensed, historically-maintained Jürisoo dataset is the source of record for match results and historical comparison, in preference to any of the 2026-specific Kaggle/GitHub datasets found.

**Why**: Verified by direct download — 104/104 2026 WC matches present, correct through the final, license confirmed CC0 (zero reuse risk), scoring convention documented (FT+ET, excludes shootouts). The alternative 2026-specific datasets looked more complete on paper but were not built to the same standard.

**Risk in the rejected alternatives**: The most feature-rich 2026-specific dataset (mominullptr) markets itself as having "zero synthetic data," but its own generation script was found, on direct inspection, to fabricate player market values via a seeded random-number formula and to hardcode xG figures with no source citation. Had this been adopted without inspection, synthetic numbers would have entered the pipeline labeled as real.

**What this does NOT solve**: Stage/round labeling and lineups are not in this dataset. Addressed separately below.

---

## 2026-07-21 — Tactical efficiency theme: downgrade, pending confirmation

**Decision**: Treat "tactical efficiency" as at-risk in its originally scoped form (event-level xG, pressures, possession value).

**Why**: Direct inspection of StatsBomb's live `competitions.json` shows no 2026 FIFA World Cup entry in their free open-data tier. No other free, reputable, event-level source was identified in this pass.

**Action needed before final scoping**: Either confirm FIFA's own match-centre aggregate stats (shots, possession, final-third entries — seen directly on the final's match page) can substitute at a shallower grain, or formally cut this theme. Not yet decided — flagged here so it isn't silently dropped later without a record of why.

---

## 2026-07-21 — Stage and Group dimensions: sourced from Yahoo Sports, not Wikipedia, not the unlicensed repo

**Decision**: Round date-boundaries and the 12-group draw are sourced from a Yahoo Sports schedule article, not Wikipedia.

**Why**: Per this project's own research-rules hierarchy, Wikipedia is a community source and ranks below "reputable sports-data providers." FIFA.com — the actually-preferred tier — was attempted directly and found technically inaccessible (JS-rendered SPA, no server-rendered content retrievable with current tooling). Yahoo Sports is professionally staffed editorial content, sits one tier below official, and was directly fetchable and directly verifiable.

**Validation performed, not assumed**: The date-window logic derived from this source was run against the independently-sourced Jürisoo match data. Result: exact 72/16/8/4/2/1/1 stage-count match, zero unmatched rows, zero group-assignment mismatches (every group-stage match has both teams landing in the same group under the derived crosswalk).

**Correction applied**: Team-name spellings differ between the two sources ("Turkey" vs. "Türkiye," "Czech Republic" vs. "Czechia," "United States" vs. "USA"). The crosswalk uses the Jürisoo spelling as canonical, since that dataset is the fact-table backbone. Documented so this isn't rediscovered as a mystery bug later.

**Residual risk, not yet closed**: This is still a single non-official source for the group draw. A second independent cross-check was proposed but not yet performed before treating this as load-bearing in a published claim.

---

## 2026-07-28 — Team→group crosswalk extracted into its own committed file

**Decision**: The Yahoo Sports-sourced team→group crosswalk (48 teams → 12
groups) that was implicitly embedded in `wc2026_stage_mapping.csv` is now
also committed on its own as `data/raw/wc2026_group_draw.csv`, and
`src/transform/build_stage_mapping.py` reads it explicitly rather than
having the mapping exist only inside a derived output file.

**Why**: Not a new sourcing decision — same Yahoo Sports data already
logged in the 2026-07-21 entry above, no new risk introduced. This is a
reproducibility fix: the transform script that regenerates
`wc2026_stage_mapping.csv` needs the crosswalk as a real input, not
something reverse-engineered from its own output. It also gives Build 4 a
ready-made seed table for `dim_group`.

**Validation performed**: `tests/test_stage_mapping.py` regenerates the
mapping table from `international_results_full.csv` and this crosswalk and
asserts the result matches the already-committed
`wc2026_stage_mapping.csv` row-for-row (5/5 tests pass).

---

## 2026-07-21 — FIFA.com ruled out for direct ingestion (for now)

**Decision**: Do not build a scraper against fifa.com in the current phase.

**Why**: Two direct fetch attempts (schedule article, live match-centre page) returned only empty HTML shells — confirmed JS-rendered SPA. Separately, FIFA's store subdomain explicitly prohibits automated data collection in its terms; the match-centre-specific terms were not directly located, so the legal picture is incomplete, not resolved in either direction.

**Revisit condition**: If richer per-match stats (shots, possession, xG-adjacent metrics) become necessary to salvage the tactical-efficiency theme, this decision should be revisited with (a) a headless-browser-capable tool and (b) a direct reading of the actual match-centre terms of use — not inferred from a sibling subdomain.
