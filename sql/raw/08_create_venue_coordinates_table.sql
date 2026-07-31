-- Mirrors data/raw/wc2026_venue_coordinates.csv column-for-column: the
-- 16 independently-sourced venue coordinates (see docs/decision_log.md,
-- 2026-07-30 "Build 7 research" entry), plus a second-source cross-check
-- per row (see docs/decision_log.md, issue #13 entry).
CREATE TABLE IF NOT EXISTS RAW.VENUE_COORDINATES (
    city VARCHAR,
    country VARCHAR,
    venue_name VARCHAR,
    latitude FLOAT,
    longitude FLOAT,
    source_url VARCHAR,
    second_latitude FLOAT,
    second_longitude FLOAT,
    second_source_url VARCHAR,
    cross_check_distance_m FLOAT
);

-- ALTER, not just CREATE ... IF NOT EXISTS, so this stays safe to re-run
-- against an account where the table already existed pre-issue-#13
-- (4 columns narrower).
ALTER TABLE RAW.VENUE_COORDINATES ADD COLUMN IF NOT EXISTS second_latitude FLOAT;
ALTER TABLE RAW.VENUE_COORDINATES ADD COLUMN IF NOT EXISTS second_longitude FLOAT;
ALTER TABLE RAW.VENUE_COORDINATES ADD COLUMN IF NOT EXISTS second_source_url VARCHAR;
ALTER TABLE RAW.VENUE_COORDINATES ADD COLUMN IF NOT EXISTS cross_check_distance_m FLOAT;
