INSERT INTO CORE.FACT_MATCH (
    match_id, date_id, stage_id, venue_id, home_team_id, away_team_id,
    home_score, away_score, went_to_et, went_to_so, so_winner_id, neutral_site
)
SELECT
    ROW_NUMBER() OVER (ORDER BY m.match_date, m.home_team, m.away_team),
    d.date_id,
    s.stage_id,
    v.venue_id,
    ht.team_id,
    at.team_id,
    m.home_score,
    m.away_score,
    NULL,
    sh.match_date IS NOT NULL,
    so.team_id,
    NULL
FROM RAW.MATCH m
JOIN CORE.DIM_DATE d ON d.full_date = m.match_date
JOIN CORE.DIM_STAGE s ON s.stage_name = m.stage
JOIN CORE.DIM_VENUE v ON v.city = m.venue_city AND v.country = m.venue_country
JOIN CORE.DIM_TEAM ht ON ht.team_name = m.home_team
JOIN CORE.DIM_TEAM at ON at.team_name = m.away_team
LEFT JOIN RAW.SHOOTOUT sh
    ON sh.match_date = m.match_date
   AND sh.home_team = m.home_team
   AND sh.away_team = m.away_team
LEFT JOIN CORE.DIM_TEAM so ON so.team_name = sh.winner
