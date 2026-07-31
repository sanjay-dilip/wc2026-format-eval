-- Build 5's historical-comparison output: the same 4 metrics computed
-- identically across every tournament in CORE.DIM_TOURNAMENT, deliberately
-- restricted to metrics derivable from fact_match's score columns alone -
-- no ranking baseline (Build 6, still gated on rankings sourcing) and no
-- stage/group breakdown (not populated for the historical rows, see
-- docs/decision_log.md). A view, not a populated table like
-- ANALYTICS.TEAM_TRAVEL_REST: it's a plain GROUP BY over CORE.FACT_MATCH,
-- so it's always current with no separate idempotency mechanism needed.
--
-- Metric definitions:
--   match_count            - COUNT(*), grain is one row per match.
--   avg_goals_per_match     - AVG(home_score + away_score), FT+ET combined
--                              per this project's source data (no separate
--                              regulation-time score exists).
--   pct_one_goal_margin     - % of matches decided by exactly 1 goal
--                              (|home_score - away_score| = 1).
--   pct_drawn_after_et       - % of matches level after FT+ET (includes
--                              knockout matches that went to a shootout,
--                              since a shootout only happens after a draw).
--   shootout_decided_matches - COUNT of matches where went_to_so = TRUE.
CREATE OR REPLACE VIEW ANALYTICS.TOURNAMENT_FORMAT_COMPARISON AS
SELECT
    t.tournament_year,
    t.team_count,
    t.format_label,
    COUNT(*) AS match_count,
    ROUND(AVG(f.home_score + f.away_score), 2) AS avg_goals_per_match,
    ROUND(100.0 * SUM(CASE WHEN ABS(f.home_score - f.away_score) = 1 THEN 1 ELSE 0 END) / COUNT(*), 1)
        AS pct_one_goal_margin,
    ROUND(100.0 * SUM(CASE WHEN f.home_score = f.away_score THEN 1 ELSE 0 END) / COUNT(*), 1)
        AS pct_drawn_after_et,
    SUM(CASE WHEN f.went_to_so THEN 1 ELSE 0 END) AS shootout_decided_matches
FROM CORE.FACT_MATCH f
JOIN CORE.DIM_TOURNAMENT t ON t.tournament_id = f.tournament_id
GROUP BY t.tournament_year, t.team_count, t.format_label
ORDER BY t.tournament_year
