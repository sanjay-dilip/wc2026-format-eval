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
) t
LEFT JOIN RAW.GROUP_DRAW gd ON gd.team = t.team_name
LEFT JOIN CORE.DIM_GROUP g ON g.group_letter = gd.group_letter
LEFT JOIN RAW.TEAM_CONFEDERATION tc ON tc.team = t.team_name
LEFT JOIN CORE.DIM_CONFEDERATION c ON c.confederation_name = tc.confederation_name
