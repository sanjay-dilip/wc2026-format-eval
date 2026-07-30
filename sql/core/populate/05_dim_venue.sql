-- "Dallas" is normalized to "Arlington": AT&T Stadium (Arlington, TX) was
-- temporarily rebranded "Dallas Stadium" for World Cup broadcast purposes,
-- and the upstream source recorded one match's city as "Dallas" while the
-- other 8 matches at the same physical stadium say "Arlington" - see
-- docs/decision_log.md (2026-07-30 entry). RAW.MATCH is left untouched;
-- the correction happens only at this population layer.
INSERT INTO CORE.DIM_VENUE (venue_id, venue_name, city, country, latitude, longitude)
SELECT ROW_NUMBER() OVER (ORDER BY venue_city, venue_country), NULL, venue_city, venue_country, NULL, NULL
FROM (
    SELECT DISTINCT
        CASE WHEN venue_city = 'Dallas' THEN 'Arlington' ELSE venue_city END AS venue_city,
        venue_country
    FROM RAW.MATCH
)
