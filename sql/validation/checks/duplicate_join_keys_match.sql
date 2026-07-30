SELECT match_date, home_team, away_team,
       'duplicate join key (match_date+home_team+away_team) in RAW.MATCH' AS detail
FROM RAW.MATCH
QUALIFY COUNT(*) OVER (PARTITION BY match_date, home_team, away_team) > 1
