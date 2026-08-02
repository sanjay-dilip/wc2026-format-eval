-- Mirrors data/raw/wc_historical_confederation_map.csv column-for-column:
-- confederation assignments for the 14 teams that appear in the 2022/1994
-- comparison tournaments but not the 2026 roster (RAW.TEAM_CONFEDERATION
-- already covers those 48). Compiled, not scraped - see
-- docs/decision_log.md, same provenance standard as the 2026 crosswalk.
-- Plus a second-source cross-check per row (see docs/decision_log.md,
-- issue #34 entry).
CREATE TABLE IF NOT EXISTS RAW.HISTORICAL_TEAM_CONFEDERATION (
    team VARCHAR,
    confederation_name VARCHAR,
    second_source_url VARCHAR,
    cross_check_match BOOLEAN
);

-- ALTER, not just CREATE ... IF NOT EXISTS, so this stays safe to re-run
-- against an account where the table already existed pre-issue-#34
-- (2 columns narrower).
ALTER TABLE RAW.HISTORICAL_TEAM_CONFEDERATION ADD COLUMN IF NOT EXISTS second_source_url VARCHAR;
ALTER TABLE RAW.HISTORICAL_TEAM_CONFEDERATION ADD COLUMN IF NOT EXISTS cross_check_match BOOLEAN;
