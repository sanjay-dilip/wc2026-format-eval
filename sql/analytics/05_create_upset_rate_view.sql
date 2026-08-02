-- Metric 3 (docs/metric_definitions.md). Grain: one row per tournament.
-- Eligibility (both teams' fifa_ranking non-NULL) is enforced by the inner
-- JOINs to CORE.TEAM_TOURNAMENT_RANKING below - a match with either team
-- unranked is excluded from the denominator entirely, not counted as
-- "not an upset" (which would understate the true rate). Draws are
-- excluded from upset_rate_pct's numerator/denominator (decisive matches
-- only) but reported separately via draw_rate_pct, as a % of eligible
-- matches. Win/loss uses the FT+ET combined score already in fact_match -
-- a penalty-shootout winner is not counted as the match "winner" here,
-- a deliberate simplification stated in the metric definition, not an
-- oversight.
CREATE OR REPLACE VIEW ANALYTICS.UPSET_RATE AS
WITH eligible AS (
    SELECT
        f.match_id,
        t.tournament_year,
        f.home_score,
        f.away_score,
        hr.fifa_ranking AS home_ranking,
        ar.fifa_ranking AS away_ranking
    FROM CORE.FACT_MATCH f
    JOIN CORE.DIM_TOURNAMENT t ON t.tournament_id = f.tournament_id
    JOIN CORE.TEAM_TOURNAMENT_RANKING hr
        ON hr.team_id = f.home_team_id AND hr.tournament_id = f.tournament_id
    JOIN CORE.TEAM_TOURNAMENT_RANKING ar
        ON ar.team_id = f.away_team_id AND ar.tournament_id = f.tournament_id
    WHERE hr.fifa_ranking IS NOT NULL AND ar.fifa_ranking IS NOT NULL
),
classified AS (
    SELECT
        tournament_year,
        CASE WHEN home_score = away_score THEN TRUE ELSE FALSE END AS is_draw,
        CASE
            WHEN home_score > away_score AND home_ranking > away_ranking THEN TRUE
            WHEN away_score > home_score AND away_ranking > home_ranking THEN TRUE
            ELSE FALSE
        END AS is_upset
    FROM eligible
)
SELECT
    tournament_year,
    COUNT(*) AS eligible_match_count,
    SUM(CASE WHEN is_draw THEN 1 ELSE 0 END) AS draw_count,
    COUNT(*) - SUM(CASE WHEN is_draw THEN 1 ELSE 0 END) AS decisive_match_count,
    SUM(CASE WHEN NOT is_draw AND is_upset THEN 1 ELSE 0 END) AS upset_count,
    ROUND(
        100.0 * SUM(CASE WHEN NOT is_draw AND is_upset THEN 1 ELSE 0 END)
            / NULLIF(COUNT(*) - SUM(CASE WHEN is_draw THEN 1 ELSE 0 END), 0),
        1
    ) AS upset_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN is_draw THEN 1 ELSE 0 END) / COUNT(*), 1) AS draw_rate_pct
FROM classified
GROUP BY tournament_year
ORDER BY tournament_year
