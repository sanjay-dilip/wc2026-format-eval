SELECT m.match_date, m.home_team, m.away_team,
       'team not found in RAW.GROUP_DRAW roster' AS detail
FROM RAW.MATCH m
WHERE m.home_team NOT IN (SELECT team FROM RAW.GROUP_DRAW)
   OR m.away_team NOT IN (SELECT team FROM RAW.GROUP_DRAW)
