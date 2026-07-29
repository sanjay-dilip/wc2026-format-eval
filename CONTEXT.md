# Current Status

**Phase**: Build 0 — feasibility + repo scaffolding. Not Build 1. Nothing
below "Complete."

## What actually exists right now

- Source inventory and reliability tiering for match-result and stage/group
  data: done, see `docs/data_feasibility_report.md`
- Sourcing decisions and their rationale: done, see `docs/decision_log.md`
- 104-row match/stage/group mapping table: built and validated
  (72/16/8/4/2/1/1 split, zero unmatched rows, zero group-assignment
  mismatches against the source data) — see `data/processed/wc2026_stage_mapping.csv`
- Raw source files captured locally so nothing depends on an upstream repo
  staying available — see `data/raw/`
- Full build sequence (Build 0 → Build C): drafted, see `docs/build_plan.md`
- `src/transform/build_stage_mapping.py` + `tests/test_stage_mapping.py`:
  built. The transform now regenerates `wc2026_stage_mapping.csv` from raw
  inputs (`international_results_full.csv` + the newly extracted
  `data/raw/wc2026_group_draw.csv` crosswalk) via non-overlapping date
  windows and a team→group lookup — no longer just an ad hoc chat result.
  5/5 pytest tests pass, including an exact row-for-row match against the
  committed CSV. `requirements.txt` (pytest) added alongside it.

## What does NOT exist yet — do not assume otherwise

- No Snowflake object of any kind. No account connection configured.
- No SQL written.
- No `config.py` — deferred to Build 2, per the build plan.
- No polished README — do not write one yet. That's Build C's job.

## Open blockers, unchanged from feasibility phase

1. FIFA rankings sourcing — untouched.
2. Group draw (12 groups × 48 teams) — currently sourced from a single
   secondary provider (Yahoo Sports). A second independent cross-check has
   not been done. Don't treat it as load-bearing in a published claim yet.
3. Venue coordinates — not independently re-verified. Only seen so far in
   an unlicensed, partially-fabricated third-party repo (see decision log)
   — do not reuse those numbers directly.
4. Tactical efficiency theme — no free 2026 event-level data source found.
   Go/no-go decision not yet made.

## Repo mechanics

- Local git repo initialized. Default branch is `master` — kept
  deliberately rather than renamed to `main`, so this isn't rediscovered
  as an accident later.
- Remote `origin` set to `https://github.com/sanjay-dilip/wc2026-format-eval.git`.
  The GitHub repo itself is expected to exist at that URL; not independently
  re-verified from this machine.
- Not yet done: the two-commit push itself (scaffold, then feasibility
  docs + validated mapping).

## Next step

Build 0's code gap is closed. Remaining Build 0 work is the two-commit
push described above. After that, Build 1 (problem statement lock +
architecture definition) is next per `docs/build_plan.md`.
