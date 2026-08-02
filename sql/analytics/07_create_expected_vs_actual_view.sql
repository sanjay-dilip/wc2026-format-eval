-- Metric 5 (docs/metric_definitions.md). Grain: one row per
-- (tournament, team). actual_finish_method documents which of the two
-- "actual finish" definitions applies to the row - 'stage_order' for 2026
-- (fact_match.stage_id is real there) or 'match_count_proxy' for 2022/1994
-- (stage_id is NULL on every historical row, Build 5 - no verified
-- stage/round source exists for those years). Any query against this view
-- must keep actual_finish_method visible and must not compare
-- furthest_stage_order/matches_played across tournaments as if they were
-- the same measurement - see the metric definition's caveat on why the
-- proxy is not monotonic with finishing stage. Teams with
-- fifa_ranking IS NULL are excluded entirely (inner JOIN to
-- CORE.TEAM_TOURNAMENT_RANKING) - there is no "expected" side of the
-- comparison to compute without a ranking.
CREATE OR REPLACE VIEW ANALYTICS.EXPECTED_VS_ACTUAL AS
WITH team_matches AS (
    SELECT f.tournament_id, f.home_team_id AS team_id, f.stage_id FROM CORE.FACT_MATCH f
    UNION ALL
    SELECT f.tournament_id, f.away_team_id AS team_id, f.stage_id FROM CORE.FACT_MATCH f
),
finish AS (
    SELECT
        tm.tournament_id,
        tm.team_id,
        COUNT(*) AS matches_played,
        MAX(ds.stage_order) AS furthest_stage_order
    FROM team_matches tm
    LEFT JOIN CORE.DIM_STAGE ds ON ds.stage_id = tm.stage_id
    GROUP BY tm.tournament_id, tm.team_id
)
SELECT
    t.tournament_year,
    dt.team_name,
    ttr.fifa_ranking,
    fi.matches_played,
    fi.furthest_stage_order,
    CASE WHEN t.tournament_year = 2026 THEN 'stage_order' ELSE 'match_count_proxy' END AS actual_finish_method
FROM finish fi
JOIN CORE.DIM_TOURNAMENT t ON t.tournament_id = fi.tournament_id
JOIN CORE.DIM_TEAM dt ON dt.team_id = fi.team_id
JOIN CORE.TEAM_TOURNAMENT_RANKING ttr ON ttr.team_id = fi.team_id AND ttr.tournament_id = fi.tournament_id
WHERE ttr.fifa_ranking IS NOT NULL
ORDER BY t.tournament_year, ttr.fifa_ranking
