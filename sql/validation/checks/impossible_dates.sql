SELECT match_date, home_team, away_team,
       'match_date outside the validated 2026 tournament window (2026-06-11 to 2026-07-19)' AS detail
FROM RAW.MATCH
WHERE match_date < '2026-06-11' OR match_date > '2026-07-19'
