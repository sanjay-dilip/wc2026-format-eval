-- Teams from RAW.HISTORICAL_MATCH (Build 5) that aren't in the 2026
-- roster get group_id = NULL (no 2026 group applies) and their
-- confederation resolved from RAW.HISTORICAL_TEAM_CONFEDERATION when
-- RAW.TEAM_CONFEDERATION doesn't have them (teams that recur across eras,
-- e.g. Brazil, Germany, already resolve via the 2026 crosswalk).
INSERT INTO CORE.DIM_TEAM (team_id, team_name, group_id, confederation_id, fifa_ranking)
SELECT
    ROW_NUMBER() OVER (ORDER BY t.team_name),
    t.team_name,
    g.group_id,
    c.confederation_id,
    NULL
FROM (
    SELECT home_team AS team_name FROM RAW.MATCH
    UNION
    SELECT away_team FROM RAW.MATCH
    UNION
    SELECT home_team FROM RAW.HISTORICAL_MATCH
    UNION
    SELECT away_team FROM RAW.HISTORICAL_MATCH
) t
LEFT JOIN RAW.GROUP_DRAW gd ON gd.team = t.team_name
LEFT JOIN CORE.DIM_GROUP g ON g.group_letter = gd.group_letter
LEFT JOIN RAW.TEAM_CONFEDERATION tc ON tc.team = t.team_name
LEFT JOIN RAW.HISTORICAL_TEAM_CONFEDERATION htc ON htc.team = t.team_name
LEFT JOIN CORE.DIM_CONFEDERATION c
    ON c.confederation_name = COALESCE(tc.confederation_name, htc.confederation_name)
