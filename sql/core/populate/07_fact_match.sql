INSERT INTO CORE.FACT_MATCH (
    match_id, tournament_id, date_id, stage_id, venue_id, home_team_id, away_team_id,
    home_score, away_score, went_to_et, went_to_so, so_winner_id, neutral_site
)
SELECT
    ROW_NUMBER() OVER (ORDER BY m.match_date, m.home_team, m.away_team),
    tour.tournament_id,
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
-- "Dallas" -> "Arlington" normalization matches 05_dim_venue.sql - same
-- physical stadium, see docs/decision_log.md (2026-07-30 entry).
JOIN CORE.DIM_VENUE v
    ON v.city = CASE WHEN m.venue_city = 'Dallas' THEN 'Arlington' ELSE m.venue_city END
   AND v.country = m.venue_country
JOIN CORE.DIM_TEAM ht ON ht.team_name = m.home_team
JOIN CORE.DIM_TEAM at ON at.team_name = m.away_team
JOIN CORE.DIM_TOURNAMENT tour ON tour.tournament_year = 2026
LEFT JOIN RAW.SHOOTOUT sh
    ON sh.match_date = m.match_date
   AND sh.home_team = m.home_team
   AND sh.away_team = m.away_team
LEFT JOIN CORE.DIM_TEAM so ON so.team_name = sh.winner
