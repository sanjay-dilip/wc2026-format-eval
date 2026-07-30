INSERT INTO ANALYTICS.TEAM_TRAVEL_REST (
    team_id, match_id, match_date, venue_id,
    previous_match_id, previous_venue_id, previous_match_date,
    distance_km, rest_days
)
WITH team_matches AS (
    SELECT match_id, home_team_id AS team_id, date_id, venue_id FROM CORE.FACT_MATCH
    UNION ALL
    SELECT match_id, away_team_id AS team_id, date_id, venue_id FROM CORE.FACT_MATCH
),
team_matches_dated AS (
    SELECT tm.match_id, tm.team_id, d.full_date AS match_date, tm.venue_id
    FROM team_matches tm
    JOIN CORE.DIM_DATE d ON d.date_id = tm.date_id
),
ordered AS (
    SELECT
        team_id,
        match_id,
        match_date,
        venue_id,
        LAG(match_id) OVER (PARTITION BY team_id ORDER BY match_date) AS previous_match_id,
        LAG(match_date) OVER (PARTITION BY team_id ORDER BY match_date) AS previous_match_date,
        LAG(venue_id) OVER (PARTITION BY team_id ORDER BY match_date) AS previous_venue_id
    FROM team_matches_dated
)
SELECT
    o.team_id,
    o.match_id,
    o.match_date,
    o.venue_id,
    o.previous_match_id,
    o.previous_venue_id,
    o.previous_match_date,
    CASE WHEN o.previous_venue_id IS NULL THEN NULL
         ELSE ST_DISTANCE(
             ST_MAKEPOINT(v.longitude, v.latitude),
             ST_MAKEPOINT(pv.longitude, pv.latitude)
         ) / 1000.0
    END AS distance_km,
    CASE WHEN o.previous_match_date IS NULL THEN NULL
         ELSE DATEDIFF('day', o.previous_match_date, o.match_date)
    END AS rest_days
FROM ordered o
JOIN CORE.DIM_VENUE v ON v.venue_id = o.venue_id
LEFT JOIN CORE.DIM_VENUE pv ON pv.venue_id = o.previous_venue_id
