-- Metric 4 (docs/metric_definitions.md). Grain: one row per
-- (tournament, confederation). team_matches unpivots fact_match into one
-- row per team per match (same pattern as
-- src/geospatial/build_travel_rest.py's per-team view of a match) so
-- win_rate and avg_goal_diff are computed from each team's own
-- perspective. win_rate uses draws = 0.5, same FT+ET-combined-score
-- convention as Upset Rate - a shootout-decided match counts as a draw
-- here, not a win for the shootout winner (deliberate simplification,
-- stated in the metric definition). confederation_id has zero NULLs
-- across all 3 tournaments, so no null handling is needed.
CREATE OR REPLACE VIEW ANALYTICS.CONFEDERATION_PERFORMANCE AS
WITH team_matches AS (
    SELECT f.tournament_id, f.home_team_id AS team_id, f.home_score AS goals_for, f.away_score AS goals_against
    FROM CORE.FACT_MATCH f
    UNION ALL
    SELECT f.tournament_id, f.away_team_id AS team_id, f.away_score AS goals_for, f.home_score AS goals_against
    FROM CORE.FACT_MATCH f
),
scored AS (
    SELECT
        tm.tournament_id,
        dt.confederation_id,
        tm.goals_for - tm.goals_against AS goal_diff,
        CASE
            WHEN tm.goals_for > tm.goals_against THEN 1.0
            WHEN tm.goals_for = tm.goals_against THEN 0.5
            ELSE 0.0
        END AS win_equivalent
    FROM team_matches tm
    JOIN CORE.DIM_TEAM dt ON dt.team_id = tm.team_id
)
SELECT
    t.tournament_year,
    c.confederation_name,
    COUNT(*) AS matches_played,
    ROUND(AVG(s.win_equivalent), 3) AS win_rate,
    ROUND(AVG(s.goal_diff), 2) AS avg_goal_diff
FROM scored s
JOIN CORE.DIM_TOURNAMENT t ON t.tournament_id = s.tournament_id
JOIN CORE.DIM_CONFEDERATION c ON c.confederation_id = s.confederation_id
GROUP BY t.tournament_year, c.confederation_name
ORDER BY t.tournament_year, c.confederation_name
