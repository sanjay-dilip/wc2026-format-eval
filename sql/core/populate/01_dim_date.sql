INSERT INTO CORE.DIM_DATE (date_id, full_date, year, month, day, day_of_week)
SELECT
    ROW_NUMBER() OVER (ORDER BY d) AS date_id,
    d AS full_date,
    YEAR(d) AS year,
    MONTH(d) AS month,
    DAY(d) AS day,
    DAYNAME(d) AS day_of_week
FROM (
    SELECT DATEADD('day', SEQ4(), (SELECT MIN(match_date) FROM RAW.MATCH)) AS d
    FROM TABLE(GENERATOR(ROWCOUNT => 60))
)
WHERE d <= (SELECT MAX(match_date) FROM RAW.MATCH)
