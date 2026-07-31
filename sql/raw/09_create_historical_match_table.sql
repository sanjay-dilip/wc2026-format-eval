-- Mirrors data/processed/wc_historical_matches.csv column-for-column: the
-- 2022 (32-team) and 1994 (24-team) World Cup matches this project uses
-- as a historical baseline for 2026 (Build 5, docs/decision_log.md). No
-- stage/group columns - no verified stage/round source exists for these
-- years in this project.
CREATE TABLE IF NOT EXISTS RAW.HISTORICAL_MATCH (
    tournament_year NUMBER,
    match_date DATE,
    home_team VARCHAR,
    away_team VARCHAR,
    home_score NUMBER,
    away_score NUMBER,
    venue_city VARCHAR,
    venue_country VARCHAR,
    neutral_site BOOLEAN
);
