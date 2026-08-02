-- Metric 2 (docs/metric_definitions.md). Grain: one row per group.
-- 2026-only: CORE.DIM_GROUP/DIM_TEAM.group_id is 2026-specific by design
-- (Build 4) - the 2022/1994 comparison tournaments have no group data in
-- this project, so this view has nothing to filter by tournament_year on,
-- it is inherently 2026-only. teams_counted vs teams_in_group flags groups
-- where a late playoff qualifier (fifa_ranking IS NULL) shrinks the
-- average's denominator - must be read alongside avg_fifa_ranking, not
-- silently treated as complete.
CREATE OR REPLACE VIEW ANALYTICS.GROUP_DIFFICULTY AS
SELECT
    g.group_id,
    g.group_letter,
    COUNT(dt.team_id) AS teams_in_group,
    COUNT(ttr.fifa_ranking) AS teams_counted,
    ROUND(AVG(ttr.fifa_ranking), 1) AS avg_fifa_ranking
FROM CORE.DIM_GROUP g
JOIN CORE.DIM_TEAM dt ON dt.group_id = g.group_id
JOIN CORE.DIM_TOURNAMENT tour ON tour.tournament_year = 2026
LEFT JOIN CORE.TEAM_TOURNAMENT_RANKING ttr
    ON ttr.team_id = dt.team_id AND ttr.tournament_id = tour.tournament_id
GROUP BY g.group_id, g.group_letter
ORDER BY g.group_letter
