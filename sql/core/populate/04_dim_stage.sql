INSERT INTO CORE.DIM_STAGE (stage_id, stage_name, stage_order, date_window_start, date_window_end)
SELECT
    so.stage_order,
    m.stage,
    so.stage_order,
    MIN(m.match_date),
    MAX(m.match_date)
FROM RAW.MATCH m
JOIN (
    SELECT 'Group Stage' AS stage_name, 1 AS stage_order
    UNION ALL SELECT 'Round of 32', 2
    UNION ALL SELECT 'Round of 16', 3
    UNION ALL SELECT 'Quarterfinals', 4
    UNION ALL SELECT 'Semifinals', 5
    UNION ALL SELECT 'Third Place Playoff', 6
    UNION ALL SELECT 'Final', 7
) so ON so.stage_name = m.stage
GROUP BY so.stage_order, m.stage
