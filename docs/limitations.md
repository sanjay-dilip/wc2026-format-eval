# Limitations

What this project does not cover, does not guarantee, or requires care
interpreting. Every item here traces to a specific build or decision-log
entry where it was actually found — nothing below is new research done
for this document; it's a consolidation of caveats that were previously
scattered across `docs/decision_log.md` and `CONTEXT.md`.

## Data gaps

- **`CORE.FACT_MATCH.went_to_et` and `.neutral_site` are `NULL` for all
  104 2026 matches.** `RAW.MATCH` scores are FT+ET combined with no
  separate regulation-time field, so extra-time can't be derived from
  data currently in `RAW`. The source has a `neutral` flag but it was
  never carried through the Build 0 transform. `went_to_so` **is**
  correctly populated (4 matches TRUE, 100 FALSE). Found and documented in
  Build 4.
- **`rest_days` (`ANALYTICS.TEAM_TRAVEL_REST`) has no time-zone
  handling.** Defined as `DATEDIFF('day', previous_match_date,
  match_date)` — no kickoff-time-of-day data exists anywhere in this
  project's sources, so there's nothing to convert. Two teams with the
  same `rest_days` value can have different true wall-clock rest. Decided
  and documented explicitly in Build 7, not glossed over.
- **`AUDIT.LOAD_LOG.credits_used` is `NULL` for every row (66 rows,
  covering all builds).** `ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY` has
  up to ~3 hours of latency, so per-load credit attribution can't be
  captured synchronously. Never backfilled. `docs/cost_report.md`
  substitutes whole-warehouse hourly totals instead, which is accurate at
  the warehouse level but can't attribute credits to a specific load.

## Scope cuts

- **Tactical efficiency theme is cut entirely, not gated.** Re-checked
  live post-tournament (issue #37, 2026-08-02): StatsBomb open-data has no
  2026 entry, FIFA.com's own match-centre pages are a JS-only empty shell,
  the one third-party dataset found (`mominullptr/FIFA-World-Cup-2026-Dataset`)
  is disqualified for fabricated data and no license, and the one
  genuinely free/licensed source (`onsidearena.com/data`) covers only
  fixtures/predictions, not match stats. No metric in this project touches
  passing accuracy, xG, possession, or any event-level tactical data.
- **All statistical claims use "associated with" / "consistent with"
  language, never causal claims** (per `docs/problem_statement.md`'s own
  methodology rule, enforced in Build 6). Competitive balance and upset
  rate differences (2026 vs. pooled 2022+1994) are **not** statistically
  significant at α=0.05; confederation performance and all 3 tournaments'
  ranking-vs-finish correlations **are** significant with medium-to-large
  effect sizes. See `docs/statistical_validation_results.md` for the full
  set — don't read any of these as claims about causation.
- **Historical comparison is limited to 2 prior tournaments (2022, 1994),
  not a full historical series.** Chosen for team-crosswalk overlap with
  the existing confederation map (Build 5) — not a representative sample
  across formats or eras. 1994 is the most recent entry in the 24-team era
  specifically, not chosen for being US-hosted (a hypothesis raised and
  explicitly ruled out during Build 5's review).

## Sourcing caveats (resolved, but single-tournament snapshots)

FIFA rankings, the group draw, venue coordinates, and the confederation
crosswalk were each independently sourced and later cross-checked against
a second independent source (issues #39, #33, #13, #34 respectively — see
`docs/decision_log.md` for each). All agree with their second source. But
every one of them is a **snapshot for this one tournament cycle**, not a
live or refreshable feed:
- FIFA ranking snapshots are pinned to specific historical dates (one per
  tournament) — there's no mechanism to pull a new snapshot for a future
  tournament without repeating the sourcing work by hand.
- The group draw, venue coordinates, and confederation crosswalk are all
  static CSVs checked into `data/raw/` — the same applies.

## Reproducibility / infrastructure

- **This pipeline depends on a Snowflake trial account that expires
  ~2026-08-07.** A stranger cloning this repo needs their own Snowflake
  account (trial or paid) — the live demo figures and cost report in this
  repo are a point-in-time snapshot from the original account, not
  something a clone can literally re-run against the same warehouse.
- **The Build 9 secondary (consumer) account is a separate trial with its
  own expiry**, not tied to the primary account's window. Cross-account
  sharing (`docs/decision_log.md`, Build 9) can't be demonstrated by a
  stranger without provisioning two accounts in the same region.
- **`CORE.INCREMENTAL_FACT_MATCH_TASK` (Build 8) is created suspended,
  never scheduled.** A continuously polling task wasn't worth the trial's
  credit budget. The incremental-load logic itself is proven (`src/
  incremental/demo_incremental_load.py`, re-run twice end-to-end), but
  nothing in this repo runs it on a schedule — it's demonstrated, not
  deployed.
- **Sharing a new view to the `SHARED` schema requires a manual, explicit
  `GRANT`.** Snowflake rejects bulk (`ALL`/`FUTURE`) grants of views to a
  share outright (found in Build 9) — each of the 8 currently shared views
  is granted individually by name. A 9th shared view added later needs its
  own `GRANT` line; there's no automation that would catch a missing one.
- **The Power BI `.pbix` binary is not committed** (gitignored,
  non-diffable) — only the `.pbip` project (semantic model + report
  metadata as TMDL/PBIR text) is tracked. Opening the project fresh
  requires Power BI Desktop with the "Power BI Project (.pbip)" preview
  feature enabled, and setting the real Snowflake account identifier via
  Power Query's Manage Parameters (the committed TMDL only has a
  placeholder — the account locator is never hardcoded, matching this
  project's `.env`-only credential convention). See `docs/decision_log.md`,
  Build 10 entry, for the exact steps and a pitfall encountered (leading
  whitespace in the parameter value producing an "Invalid URI" error).

## Documentation

- **`docs/decision_log.md` is comprehensive but not yet polished** — it
  reads as a running session log (dated entries added incrementally over
  10 builds), not an edited reference document. A cleanup pass is planned
  before the `v1.0` tag but hadn't happened as of this document's writing.
