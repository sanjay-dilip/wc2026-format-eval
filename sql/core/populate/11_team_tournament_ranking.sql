INSERT INTO CORE.TEAM_TOURNAMENT_RANKING (team_id, tournament_id, fifa_ranking, ranking_as_of_date)
SELECT
    t.team_id,
    tour.tournament_id,
    r.fifa_ranking,
    r.ranking_as_of_date
FROM RAW.FIFA_RANKING_SNAPSHOT r
JOIN CORE.DIM_TEAM t ON t.team_name = r.team
JOIN CORE.DIM_TOURNAMENT tour ON tour.tournament_year = r.tournament_year
