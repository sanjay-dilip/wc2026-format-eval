INSERT INTO CORE.DIM_VENUE (venue_id, venue_name, city, country, latitude, longitude)
SELECT ROW_NUMBER() OVER (ORDER BY venue_city, venue_country), NULL, venue_city, venue_country, NULL, NULL
FROM (SELECT DISTINCT venue_city, venue_country FROM RAW.MATCH)
