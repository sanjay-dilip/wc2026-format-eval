# Problem Statement — 2026 World Cup Format Evaluation

Status: locked for Build 1. Revises the provisional statement using Build 0
feasibility findings. Superseded only by a future decision-log entry, not by
silent rewrite.

## Core question

Tournament format planners need to determine whether FIFA's expansion to 48
teams increased global representation without materially degrading
competitive balance or scheduling fairness relative to prior World Cup
formats.

## What changed from the provisional version, and why

The provisional statement (pre-Build 0) treated "match quality" as covering
tactical efficiency at event-level grain (xG, pressures, possession value)
on the same footing as competitive balance and scheduling fairness. Build 0
found:

- **No free, reputable event-level data source exists for the 2026
  tournament** (`docs/data_feasibility_report.md`, Source 2 — StatsBomb's
  open tier stops at 2022). Event-level tactical efficiency is downgraded
  out of the core question, not silently dropped: it remains an open,
  gated theme (see below), not a founding pillar of the analysis.
- **FIFA rankings sourcing is still unresolved** (`docs/decision_log.md`,
  open gap). Any metric that depends on a ranking or Elo baseline —
  ranking-adjusted competitive balance, expected-vs-actual performance,
  upset rate — is contingent on Build 6 closing that gap. Until then, this
  project computes competitive-balance metrics from match outcomes and
  goal differentials only, not from ranking-adjusted expectations.

Removing these threads from the core question is a scope correction, not a
weakening of the project: it keeps the falsifiable claim limited to what
Build 0 actually confirmed is buildable from real, licensable data.

## Gated / conditional themes (not part of the core question, not dropped)

- **Travel/rest burden**: gated on independent venue-coordinate
  re-verification (Build 7) — currently only seen in an unlicensed,
  partially-fabricated repo and not reusable as-is.
- **Cross-account data sharing**: gated on a written Build 9 go/no-go, not
  assumed necessary for the core question.

## Themes cut, not gated

- **Tactical efficiency** (event-level xG/pressures/possession value, and
  the shallower aggregate box-score substitute both considered): final
  **no-go**, `docs/decision_log.md` 2026-08-02 "Issue #37" entry.
  Re-checked after the tournament concluded (2026-07-19) specifically to
  confirm this wasn't a temporary gap — StatsBomb's open tier still has no
  2026 entry, FIFA's own pages are still technically inaccessible, and no
  free/licensed/systematic alternative was found. Out of scope for this
  project; won't be revisited without new evidence.

## Method

The project builds a Snowflake-based analytics platform ingesting match
results, historical tournament comparisons, confederation data, and (once
resolved) ranking data — testing the core question with normalized,
stage-aware metrics rather than raw totals, so that a 48-team tournament is
never compared against a 32-team tournament using unadjusted counts.

Snowflake's layered ingestion, validation, and governed transformation
(`RAW` → `VALIDATION` → `CORE` → `ANALYTICS`, audited throughout) exists to
make every metric traceable to source data and reproducible on rerun — not
to make the SQL harder than it needs to be than a simpler stack would
require. Every Snowflake feature used has to earn that role individually;
see `docs/architecture.md` for the feature-by-feature justification.

## Audience

A FIFA tournament strategy analyst or format-planning stakeholder deciding
whether the 48-team structure should be retained, adjusted, or reconsidered
for future cycles.

## Stance on outcome

The conclusion may be mixed. Representation gains and competitive-balance
costs are not mutually exclusive findings. The project does not assume
expansion succeeded or failed going in, and every statistical claim in
later builds must use "associated with" / "consistent with" language, not
causal claims, per Build 6's own validation rules.
