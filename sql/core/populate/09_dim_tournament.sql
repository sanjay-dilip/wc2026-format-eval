-- team_count is COUNT(DISTINCT team), computed from the matches actually
-- loaded for each tournament, not hardcoded - a hardcoded 48/32/24 could
-- silently drift out of sync with the data.
INSERT INTO CORE.DIM_TOURNAMENT (tournament_id, tournament_year, team_count, format_label)
SELECT
    ROW_NUMBER() OVER (ORDER BY tournament_year),
    tournament_year,
    team_count,
    team_count || '-team' AS format_label
FROM (
    SELECT 2026 AS tournament_year, COUNT(DISTINCT team) AS team_count
    FROM (
        SELECT home_team AS team FROM RAW.MATCH
        UNION
        SELECT away_team FROM RAW.MATCH
    )
    UNION ALL
    SELECT tournament_year, COUNT(DISTINCT team) AS team_count
    FROM (
        SELECT tournament_year, home_team AS team FROM RAW.HISTORICAL_MATCH
        UNION
        SELECT tournament_year, away_team FROM RAW.HISTORICAL_MATCH
    )
    GROUP BY tournament_year
)
