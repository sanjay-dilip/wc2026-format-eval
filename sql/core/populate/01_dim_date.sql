-- LATERAL, not a plain comma-join, on purpose: a plain cross join between
-- a multi-row relation (r, one row per tournament) and
-- TABLE(GENERATOR(ROWCOUNT => 60)) does NOT re-run the generator per r
-- row in Snowflake - SEQ4() ends up round-robin-distributed across all r
-- rows instead of restarting at 0 for each one (confirmed directly: it
-- produced dates strided by 3, one third of the intended range per
-- tournament). LATERAL forces per-row evaluation, which is what this
-- needs to generate an independent 60-day window per tournament.
INSERT INTO CORE.DIM_DATE (date_id, full_date, year, month, day, day_of_week)
SELECT
    ROW_NUMBER() OVER (ORDER BY d) AS date_id,
    d AS full_date,
    YEAR(d) AS year,
    MONTH(d) AS month,
    DAY(d) AS day,
    DAYNAME(d) AS day_of_week
FROM (
    SELECT DISTINCT d
    FROM (
        SELECT DATEADD('day', g.s, r.min_date) AS d, r.max_date AS max_date
        FROM (
            SELECT MIN(match_date) AS min_date, MAX(match_date) AS max_date FROM RAW.MATCH
            UNION ALL
            SELECT MIN(match_date) AS min_date, MAX(match_date) AS max_date
            FROM RAW.HISTORICAL_MATCH
            GROUP BY tournament_year
        ) r,
        LATERAL (SELECT SEQ4() AS s FROM TABLE(GENERATOR(ROWCOUNT => 60))) g
    )
    WHERE d <= max_date
)
