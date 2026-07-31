-- Appends Build 5's historical comparison matches to CORE.FACT_MATCH -
-- does NOT truncate first, unlike every other populate query in this
-- directory: 07_fact_match.sql already truncated+repopulated the 2026
-- rows earlier in the same src/core/build_core.py run, and this needs to
-- add to that, not wipe it. match_id continues from 07's max so the two
-- inserts never collide.
--
-- stage_id and venue_id are NULL: no verified stage/round or
-- venue-coordinate source exists for these years in this project (see
-- docs/decision_log.md) - not guessed, same pattern as Build 4's
-- went_to_et/neutral_site decision for the 2026 rows.
INSERT INTO CORE.FACT_MATCH (
    match_id, tournament_id, date_id, stage_id, venue_id, home_team_id, away_team_id,
    home_score, away_score, went_to_et, went_to_so, so_winner_id, neutral_site
)
SELECT
    (SELECT COALESCE(MAX(match_id), 0) FROM CORE.FACT_MATCH)
        + ROW_NUMBER() OVER (ORDER BY m.tournament_year, m.match_date, m.home_team, m.away_team),
    tour.tournament_id,
    d.date_id,
    NULL,
    NULL,
    ht.team_id,
    at.team_id,
    m.home_score,
    m.away_score,
    NULL,
    sh.match_date IS NOT NULL,
    so.team_id,
    m.neutral_site
FROM RAW.HISTORICAL_MATCH m
JOIN CORE.DIM_DATE d ON d.full_date = m.match_date
JOIN CORE.DIM_TEAM ht ON ht.team_name = m.home_team
JOIN CORE.DIM_TEAM at ON at.team_name = m.away_team
JOIN CORE.DIM_TOURNAMENT tour ON tour.tournament_year = m.tournament_year
LEFT JOIN RAW.SHOOTOUT sh
    ON sh.match_date = m.match_date
   AND sh.home_team = m.home_team
   AND sh.away_team = m.away_team
LEFT JOIN CORE.DIM_TEAM so ON so.team_name = sh.winner
