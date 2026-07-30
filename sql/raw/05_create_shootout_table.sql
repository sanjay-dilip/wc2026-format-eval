-- Mirrors data/raw/shootouts_full.csv column-for-column: full historical
-- shootout dataset, raw landing, no filtering to 2026.
CREATE TABLE IF NOT EXISTS RAW.SHOOTOUT (
    match_date DATE,
    home_team VARCHAR,
    away_team VARCHAR,
    winner VARCHAR,
    first_shooter VARCHAR
);
