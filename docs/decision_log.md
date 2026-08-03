# Decision Log — 2026 World Cup Format Evaluation

Every sourcing and design decision made on this project, condensed and
grouped by the stage it belongs to in `README.md`'s "Project Workflow"
section. Each entry states the decision, the reason, and the key verified
numbers — narrative detail has been trimmed for readability; the git
history and referenced GitHub issues hold the full discussion where
needed.

---

## Feasibility research and source validation

### Match-results backbone
Source of record: `martj42/international_results` (CC0-licensed,
historically maintained) — chosen over several 2026-specific
Kaggle/GitHub datasets. Verified 104/104 2026 matches present, correct
through the final. The most feature-rich alternative
(`mominullptr/FIFA-World-Cup-2026-Dataset`) markets "zero synthetic
data" but its own generation script fabricates player market values and
hardcodes xG with no citation — rejected after direct inspection, not
on reputation alone.

### Stage and group dimensions
Round dates and the 12-group draw sourced from a Yahoo Sports schedule
article (FIFA.com itself is a JS-rendered SPA, not scrapeable).
Validated against the independently-sourced match data: exact
72/16/8/4/2/1/1 stage-count match, zero unmatched rows, zero
group-assignment mismatches. Team-name spellings normalized to the
match-data source as canonical (Turkey vs. Türkiye, etc.). Single-sourced
at this point — closed later by issue #33 (see below).

### FIFA.com ruled out for direct ingestion
Two fetch attempts (schedule article, match-centre page) returned only
empty JS shells. Store subdomain explicitly prohibits automated
collection; match-centre-specific terms weren't located. Not revisited
without a headless-browser-capable tool and a direct reading of the
actual terms.

### Team→group crosswalk extracted
The Yahoo Sports-sourced crosswalk, originally only implicit inside the
stage-mapping output, committed on its own as
`data/raw/wc2026_group_draw.csv` so the transform reads it as a real
input, not something reverse-engineered from its own output. Regenerated
mapping matches the committed CSV row-for-row (5/5 tests).

---

## Dimensional modeling

### Arlington/Dallas venue dedup
`RAW.MATCH` recorded one match as `venue_city = 'Dallas'` — same
physical stadium (AT&T Stadium, Arlington, TX), temporarily rebranded for
broadcast. Normalized in the `CORE` population layer only (`RAW` left
faithful to the source). `CORE.DIM_VENUE` went from 17 rows to the
correct 16.

### Zero-copy clone of CORE cut
Skipped for the initial `CORE` load — no prior data existed yet to
protect, and Time Travel already covers session risk. Revisit once
`CORE` holds data a later build could risk mutating.

### Confederation crosswalk compiled, not scraped
`data/raw/wc2026_confederation_map.csv` (48 teams → 6 confederations)
compiled from known qualifying outcomes — no source existed to scrape.
Checked against the 48-team roster: zero missing, zero extra.
Single-sourced at this point — closed later by issue #34.

### `went_to_et` / `neutral_site` left NULL
Source data has FT+ET combined scores with no regulation-time split, so
extra-time can't be derived. A `neutral` flag exists upstream but was
never carried through the stage-mapping transform. `went_to_so` is
derivable and is populated correctly.

---

## Historical comparison

### Historical Comparison Layer (2022, 1994)
`CORE.FACT_MATCH` extended to the same grain for 2022 (32-team) and 1994
(24-team), via a new `CORE.DIM_TOURNAMENT` dimension. Chosen for
team-crosswalk overlap with the existing confederation map. A 16-team-era
tournament (1970) was excluded after a real data-quality issue was found:
the source dataset retroactively applies modern country names (USSR →
"Russia") to some historical rows.

Two bugs found and fixed:
- A `GENERATOR`/`SEQ4()` cross join silently truncated `dim_date` (32
  rows instead of 99) because Snowflake doesn't restart the generator per
  outer row — fixed with a `LATERAL` subquery.
- `TEAM_TRAVEL_REST`'s `LAG()` window crossed tournament boundaries once
  a team appeared in more than one tournament — fixed by partitioning by
  `(team_id, tournament_id)`.

Verified: `DIM_DATE` = 99, `DIM_TEAM` = 62, `DIM_TOURNAMENT` = 3,
`FACT_MATCH` = 220 (104+64+52), 0 orphaned FKs. Historical rows have
`stage_id`/`venue_id` = NULL (no source exists for those), by design.

---

## Geospatial / travel-rest analysis

### Venue coordinates sourced
`data/raw/wc2026_venue_coordinates.csv` (16 venues) sourced from each
venue's own Wikipedia article — replacing the unlicensed,
partially-fabricated third-party repo ruled out during feasibility.
Checked against `RAW.MATCH`'s 16 normalized venue cities: zero missing,
zero extra. Single-sourced at this point — closed later by issue #13.

### Rest-day definition and time zone handling
`rest_days = DATEDIFF('day', previous_match_date, match_date)` — no time
zone conversion, because no kickoff time-of-day exists anywhere in the
source data; there's nothing to convert. Real cost stated plainly: two
teams with the same `rest_days` can have different true wall-clock rest.
Distance uses Snowflake's native `ST_MAKEPOINT`/`ST_DISTANCE`.

Verified: `TEAM_TRAVEL_REST` = 208 rows, 48 tournament-openers with no
previous match, 0 rows missing distance/rest otherwise. `distance_km`
0–4302.7 km, `rest_days` 3–8 (mean ~5.3).

### Venue coordinates cross-checked (issue #13)
Second source: OpenStreetMap/Nominatim (community-surveyed, not
Wikipedia-derived). All 16 venues agree within 2.7–80.2 m — well inside
tolerance. No `CORE` correction needed.

---

## Rankings resolution + analytical marts + statistical validation

### FIFA ranking sourcing
One FIFA World Ranking snapshot per tournament (2026: 19 Nov 2025; 2022:
31 Mar 2022; 1994: 19 Nov 1993), each from that tournament's own
Wikipedia seeding article citing FIFA's official release. Several
GitHub scraper repos and an Elo-rating alternative were evaluated and
rejected (no license, or not FIFA's own system).
`CORE.TEAM_TOURNAMENT_RANKING` (grain: team × tournament, not a
`dim_team` column — confirmed Brazil's ranking genuinely differs per
tournament: 4th/1st/5th). 9 of 104 rows NULL at this point (teams not
yet determined at the snapshot date) — backfilled later by issue #39.

### Analytical marts + statistical validation layer
5 `ANALYTICS` marts built as always-current views (competitive balance,
group difficulty, upset rate, confederation performance,
expected-vs-actual). One hypothesis test per metric — Mann-Whitney U,
Fisher's exact, Kruskal-Wallis, Spearman — each reporting an effect size
and "associated with" language, never causal. Full results:
`docs/statistical_validation_results.md`. A doc error was found and
fixed along the way: `metric_definitions.md` claimed 100% ranking
coverage for 2022; live data showed 29/32 (the mart SQL itself was
already correct).

### FIFA ranking cross-check + backfill (issue #39)
Second source: `en.fifaranking.net`, queried by exact date. All 95
non-NULL values matched exactly. The second source also had real values
for all 9 previously-NULL rows (not "no ranking existed," just excluded
from the seeding-table source) — backfilled with user confirmation.
Re-running the statistics changed real numbers: upset rate's p-value
moved from 0.0521 to 0.1359 on the larger, complete sample — the
headline conclusion (not statistically significant) held, better
supported.

### Tactical efficiency — final no-go (issue #37)
Re-checked post-tournament: StatsBomb open-data still has no 2026 entry,
FIFA.com's own pages are still a JS-only shell, the one third-party
dataset with full coverage is still disqualified for fabricated data,
and the one genuinely free/licensed alternative
(`onsidearena.com/data`) covers only fixtures/predictions. No viable
source exists at any grain. Theme is cut from scope, not gated —
final decision, not revisited without new evidence.

### Group draw cross-check (issue #33)
Second source: Wikipedia's 12 per-group articles, citing FIFA's own
final draw directly. All 48 teams across 12 groups match exactly — zero
disagreements. No `CORE` correction needed.

### Confederation crosswalk cross-check (issue #34)
Second source: Wikipedia's six per-confederation membership pages. All
62 teams (48 2026 + 14 historical) match exactly — zero disagreements.
No `CORE` correction needed.

---

## Incremental pipeline demonstration

### Streams + Tasks incremental load
`RAW.MATCH_STREAM` feeds `CORE.SP_APPLY_MATCH_STREAM()`, applying
corrections via `UPDATE` and new matches via `INSERT` — no truncate,
unlike every other `CORE` populate path.
`CORE.INCREMENTAL_FACT_MATCH_TASK` wraps it, created suspended (cost
decision — a continuously polling task isn't worth the trial credits).

Real constraint found: `match_id` is `ROW_NUMBER()`-assigned at
full-rebuild time, so a full rebuild after any insert renumbers the
historical block — meaning "incremental equals full rebuild" has to be
verified by hashing natural-key/business columns, not raw `match_id`.

A real bug found and fixed: `setup_snowflake.py`'s naive `.split(";")`
broke on the new stored procedure's `$$`-quoted body — fixed with the
connector's `execute_string()`.

Verified: 3 scenarios (new match, correction, idempotent rerun) all pass
by content hash, re-run twice end-to-end.

---

## Cross-account sharing

### Go/no-go: GO, bounded scope
Scoped strictly to a Secure Data Share plus a verified — not assumed —
check that `RAW` is inaccessible from the consumer side. Justified via
the project's 5-question test (problem, simplicity, cost, demonstration,
testing) — negligible cost, both accounts confirmed on `AWS_US_WEST_2`.

### Secure Data Share implementation
`SHARED` schema holds 8 secure views wrapping `ANALYTICS`; `WC2026_SHARE`
grants `SELECT` on each individually. Real constraint found: Snowflake
rejects bulk (`ALL`/`FUTURE`) grants of views to a share outright — each
view must be granted by name, documented so a 9th shared view later
needs its own `GRANT` line.

Verified from the live consumer account: a BI-shaped query against the
share succeeds; `SHOW SCHEMAS` lists only `SHARED`; a direct query
against `RAW` actually fails (`does not exist or not authorized`), not
assumed hidden.

---

## Power BI presentation layer

### Power BI layer (issue #41)
`.pbip` project: semantic model (8 tables mirroring the 8 `SHARED`
views, 20 DAX measures, no relationships between marts) built via the
`powerbi-modeling-mcp` TOM API, then exported to TMDL. Report (PBIR
format, 8 pages) hand-authored for page/report metadata, then opened in
Power BI Desktop for the actual visual authoring — visual-binding
validation needs Desktop's live editor.

Snowflake account identifier kept out of committed files — M partition
queries reference a `SnowflakeAccount` parameter, not a hardcoded
string. `.pbix` binary kept local, not committed (non-diffable; the
`.pbip` project is the source of truth).

Data verified live via DAX queries run through the MCP against the
Desktop instance's actual Snowflake-refreshed data — row counts
reconcile exactly against this project's documented figures.
