-- venue_name and latitude/longitude are NULL until sourced: no stadium-name
-- column exists in RAW yet, and coordinates stay NULL until Build 7's
-- independent re-verification (open blocker #3, docs/decision_log.md).
CREATE TABLE IF NOT EXISTS CORE.DIM_VENUE (
    venue_id NUMBER PRIMARY KEY,
    venue_name VARCHAR,
    city VARCHAR NOT NULL,
    country VARCHAR NOT NULL,
    latitude FLOAT,
    longitude FLOAT
);
