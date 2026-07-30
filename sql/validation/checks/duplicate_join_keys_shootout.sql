SELECT match_date, home_team, away_team,
       'duplicate join key (match_date+home_team+away_team) in RAW.SHOOTOUT' AS detail
FROM RAW.SHOOTOUT
QUALIFY COUNT(*) OVER (PARTITION BY match_date, home_team, away_team) > 1
