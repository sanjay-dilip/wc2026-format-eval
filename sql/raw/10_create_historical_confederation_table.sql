-- Mirrors data/raw/wc_historical_confederation_map.csv column-for-column:
-- confederation assignments for the 14 teams that appear in the 2022/1994
-- comparison tournaments but not the 2026 roster (RAW.TEAM_CONFEDERATION
-- already covers those 48). Compiled, not scraped - see
-- docs/decision_log.md, same provenance standard as the 2026 crosswalk.
CREATE TABLE IF NOT EXISTS RAW.HISTORICAL_TEAM_CONFEDERATION (
    team VARCHAR,
    confederation_name VARCHAR
);
