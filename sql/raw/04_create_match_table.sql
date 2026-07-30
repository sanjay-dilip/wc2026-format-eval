-- Mirrors data/processed/wc2026_stage_mapping.csv column-for-column: raw
-- landing, no transformation. group_letter is NULL for knockout matches.
CREATE TABLE IF NOT EXISTS RAW.MATCH (
    match_date DATE,
    home_team VARCHAR,
    away_team VARCHAR,
    home_score NUMBER,
    away_score NUMBER,
    venue_city VARCHAR,
    venue_country VARCHAR,
    stage VARCHAR,
    group_letter VARCHAR,
    is_knockout BOOLEAN
);
