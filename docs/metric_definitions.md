# Metric Definitions — Build 6 Analytical Marts

Status: written before any mart SQL exists, per Build 6's own success
criteria (`docs/build_plan.md`) and the same discipline Build 7's
`rest_days` decision already used - decide and document the definition
first, build the query second. These 5 definitions cover Build 6 Part 1's
scope (issue #19); the marts themselves, built off these definitions, are
Part 2's scope (next session's issue).

Every metric below follows the same structure: business meaning, formula,
grain, null handling, ET/shootout handling, historical comparability -
exactly the 6 things Build 6's success criteria requires a written
definition to cover.

All 5 marts are computable across all 3 tournaments in `CORE.DIM_TOURNAMENT`
(2026, 2022, 1994) using only `CORE.FACT_MATCH`, `CORE.DIM_TEAM`, and
`CORE.TEAM_TOURNAMENT_RANKING` - except where a metric is explicitly noted
below as gated to a subset of tournaments, because the data those
tournaments would need (group/stage labels, full ranking coverage) doesn't
exist in this project (see `docs/decision_log.md`, Build 5 and Build 6
entries).

Per `docs/problem_statement.md`'s explicit rule for this build: every
statistical claim built from these definitions must state its hypothesis,
check its assumptions, report an effect size and practical significance
alongside any p-value, and use "associated with" / "consistent with"
language - never causal claims. That validation work happens in Part 2,
against these definitions.

---

## 1. Competitive Balance

**Business meaning**: whether matches in a tournament tend to be close
contests or lopsided - a proxy for whether the tournament's format
produces well-matched games.

**Formula**: per tournament, `AVG(ABS(home_score - away_score))` (mean
absolute goal difference) and the % of matches decided by a margin of 3+
goals ("blowout rate").

**Grain**: one row per tournament.

**Null handling**: none needed - `home_score`/`away_score` are `NOT NULL`
on every `fact_match` row across all 3 tournaments.

**ET/shootout handling**: `home_score`/`away_score` are FT+ET combined
(this project's established convention, `docs/data_dictionary.md`) and
never include shootout kicks. A match resolved by shootout still counts
by its FT+ET goal difference (typically 0, a draw) for this metric,
consistently across all 3 tournaments.

**Historical comparability**: fully comparable across all 3 tournaments -
no ranking or stage/group dependency.

---

## 2. Group Difficulty

**Business meaning**: whether some groups in the group stage are
meaningfully harder (contain stronger opponents by ranking) than others -
relevant to draw fairness.

**Formula**: per group, `AVG(fifa_ranking)` across the group's teams
(lower average = harder group), using `CORE.TEAM_TOURNAMENT_RANKING`
joined through `CORE.DIM_TEAM.group_id`.

**Grain**: one row per (tournament, group).

**Null handling**: a group containing a team with `fifa_ranking IS NULL`
(2026's 6 late playoff qualifiers - `docs/decision_log.md`) gets an
average computed over fewer teams than the group actually has. This must
be flagged per group when shown (e.g. a "teams counted" column), not
silently averaged and presented as if complete.

**ET/shootout handling**: not applicable - this metric never touches match
outcomes, only pre-tournament rankings.

**Historical comparability**: **2026-only.** `dim_group`/`group_id` is
2026-specific by design (Build 4) - the 2022 and 1994 comparison
tournaments have no group data in this project at all (no verified source
was ever sourced for it, unlike the 2026 Yahoo Sports crosswalk - Build
0/5). This metric cannot be computed for the historical baseline; report
it as 2026-only, not silently omitted from the mart's coverage statement.

---

## 3. Upset Rate

**Business meaning**: how often the numerically higher-ranked (better)
team loses - a signal of unpredictability / competitive parity.

**Formula**: for each match where both teams have a non-NULL
`fifa_ranking`, an upset = the team with the numerically *worse* (higher)
ranking wins. `upset_rate = COUNT(upsets) / COUNT(eligible matches)` per
tournament. Draws are excluded from the upset/non-upset count (neither
team "won") but reported separately as a % of eligible matches.

**Grain**: one row per tournament.

**Null handling**: matches where *either* team's `fifa_ranking` is NULL
are excluded from the denominator entirely - not counted as "not an
upset". Silently treating a missing ranking as "not an upset" would
understate the true rate, not just shrink the sample size.

**ET/shootout handling**: win/loss uses the FT+ET combined score already
in `fact_match` (this project's standing convention). A team that wins on
penalties after a 0-0 draw is **not** counted as a match "winner" under
this definition - the shootout outcome is separate from `home_score`/
`away_score`, and this metric only reads the score columns. Stated
plainly as a deliberate simplification, not an oversight.

**Historical comparability**: comparable across all 3 tournaments in
principle (only needs `fact_match` scores + `CORE.TEAM_TOURNAMENT_RANKING`,
both populated for all 3). Ranking coverage is not 100% for any tournament
except 1994: 2026 has 42/48 teams ranked (6 late qualifiers excluded),
2022 has 29/32 (3 intercontinental/UEFA playoff winners not yet known at
the snapshot date), 1994 has 24/24 (`docs/decision_log.md`, Build 6 Part 1
entry). This correction supersedes an earlier version of this line that
stated 2022/1994 both had 100% coverage - wrong for 2022, caught while
building `ANALYTICS.UPSET_RATE` in Build 6 Part 2, which computes its
`eligible_match_count` from the live data rather than this doc's prose.
Each tournament's shrunk sample is a caveat to state alongside the number,
not a reason to skip the comparison.

---

## 4. Confederation Performance

**Business meaning**: how well each of the 6 confederations' teams
perform overall - relevant to whether expansion increased genuine
competitiveness across confederations or just added more early exits.

**Formula**: per (tournament, confederation): win rate (wins / matches
played, draws = 0.5) and average goal differential per match, using
`CORE.DIM_TEAM.confederation_id` (populated for all 62 teams across all 3
tournaments - verified zero NULLs during Build 5/6 loading).

**Grain**: one row per (tournament, confederation).

**Null handling**: none needed - `confederation_id` has zero NULLs.

**ET/shootout handling**: same FT+ET-combined-score convention as Upset
Rate above - a shootout-decided match counts as a draw (0.5 win-equivalent
each side) under this win-rate formula, not a win for the shootout
winner. Stated as a deliberate simplification for the same reason as
metric 3.

**Historical comparability**: fully comparable across all 3 tournaments -
`confederation_id` is populated regardless of tournament, no dependency on
stage/group data.

---

## 5. Expected-vs-Actual Performance

**Business meaning**: whether a team's actual tournament finish matches
what its pre-tournament FIFA ranking would predict - the most direct test
of whether the 48-team expansion changed outcomes relative to
pre-tournament form.

**Formula**: per (tournament, team), compare `fifa_ranking` (expected
strength) against actual finish. "Actual finish" is defined two different
ways depending on data availability (see Historical comparability below):
for 2026, the furthest `CORE.DIM_STAGE.stage_order` reached before
elimination; for 2022/1994, the number of matches played as a proxy (more
matches generally means advancing further, though this proxy is
imperfect - see caveat below).

**Grain**: one row per (tournament, team).

**Null handling**: teams with `fifa_ranking IS NULL` (2026 late
qualifiers) are excluded entirely - there is no "expected" side of the
comparison to compute without a ranking.

**ET/shootout handling**: not directly relevant to "how far a team
advanced" - a team eliminated on penalties still reached and lost in that
round, identical to a regulation-time elimination. No special handling
needed.

**Historical comparability**: **only partially comparable, and this must
be stated every time the metric is shown, not just once in this doc.**
2026 has a real stage-level "actual finish" (`fact_match.stage_id`, via
`CORE.DIM_STAGE`). 2022 and 1994 have `stage_id = NULL` on every
historical `fact_match` row (Build 5 - no verified stage/round source
exists for those years in this project), so their "actual finish" can
only use the match-count proxy. That proxy has a real, known flaw: a
team eliminated in the Round of 16 after finishing top of its group can
have played the same number of matches as a team that finished bottom of
its group and never advanced at all, if the tournament's bracket size
happens to align that way - match count is not a monotonic stand-in for
finishing stage. Any published comparison using this metric must treat
2026's numbers as the load-bearing ones and 2022/1994's as directional
only, clearly labeled, not presented as equivalent precision.

---

## Cross-cutting caveats that apply to every metric above

- **FIFA ranking is a snapshot per tournament, not a time series.**
  `CORE.TEAM_TOURNAMENT_RANKING` holds one ranking value per team per
  tournament, taken from each tournament's own official
  seeding/qualification ranking date (2026: 19 Nov 2025; 2022: 31 Mar
  2022; 1994: 19 Nov 1993 - `docs/decision_log.md`), not a
  continuously-updated rating. A team's ranking on match day within a
  tournament is the same value used for every one of that team's matches
  in that tournament, even late in a multi-week event.
- **Rankings are single-sourced to Wikipedia's tournament-specific
  seeding/qualification articles**, which in turn cite FIFA's own
  official ranking releases - same tier and reasoning already applied to
  venue coordinates (public, officially-published facts, individually
  citable), not an independent secondary cross-check the way the group
  draw and venue coordinates eventually got (`docs/decision_log.md`,
  issue #13). Not yet cross-checked against a second source - same
  caveat status as the group draw and confederation crosswalk. Treat as
  usable, not yet load-bearing in a published claim without that
  cross-check, consistent with this project's standing rule for
  single-sourced data.
