-- Metric 1 (docs/metric_definitions.md). Grain: one row per tournament.
-- avg_abs_goal_diff and blowout_rate_pct both read home_score/away_score
-- directly - FT+ET combined, never shootout kicks (this project's standing
-- convention) - so a shootout-decided match still counts by its (typically
-- 0) FT+ET goal difference. Fully comparable across all 3 tournaments, no
-- ranking or stage/group dependency.
CREATE OR REPLACE VIEW ANALYTICS.COMPETITIVE_BALANCE AS
SELECT
    t.tournament_year,
    t.team_count,
    t.format_label,
    COUNT(*) AS match_count,
    ROUND(AVG(ABS(f.home_score - f.away_score)), 2) AS avg_abs_goal_diff,
    ROUND(
        100.0 * SUM(CASE WHEN ABS(f.home_score - f.away_score) >= 3 THEN 1 ELSE 0 END) / COUNT(*),
        1
    ) AS blowout_rate_pct
FROM CORE.FACT_MATCH f
JOIN CORE.DIM_TOURNAMENT t ON t.tournament_id = f.tournament_id
GROUP BY t.tournament_year, t.team_count, t.format_label
ORDER BY t.tournament_year
