-- Mirrors data/raw/wc2026_venue_coordinates.csv column-for-column: the
-- 16 independently-sourced venue coordinates (see docs/decision_log.md,
-- 2026-07-30 "Build 7 research" entry).
CREATE TABLE IF NOT EXISTS RAW.VENUE_COORDINATES (
    city VARCHAR,
    country VARCHAR,
    venue_name VARCHAR,
    latitude FLOAT,
    longitude FLOAT,
    source_url VARCHAR
);
