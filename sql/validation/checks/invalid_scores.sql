SELECT match_date, home_team, away_team,
       'invalid score: home=' || home_score || ' away=' || away_score AS detail
FROM RAW.MATCH
WHERE home_score < 0 OR home_score > 20 OR away_score < 0 OR away_score > 20
