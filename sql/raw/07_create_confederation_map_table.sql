-- Mirrors data/raw/wc2026_confederation_map.csv column-for-column: the
-- 48-team-to-confederation crosswalk, compiled per decision_log.md
-- (2026-07-30 entry), needed so dim_team/dim_confederation can be built
-- from warehouse data. Plus a second-source cross-check per row (see
-- docs/decision_log.md, issue #34 entry).
CREATE TABLE IF NOT EXISTS RAW.TEAM_CONFEDERATION (
    team VARCHAR,
    confederation_name VARCHAR,
    second_source_url VARCHAR,
    cross_check_match BOOLEAN
);

-- ALTER, not just CREATE ... IF NOT EXISTS, so this stays safe to re-run
-- against an account where the table already existed pre-issue-#34
-- (2 columns narrower).
ALTER TABLE RAW.TEAM_CONFEDERATION ADD COLUMN IF NOT EXISTS second_source_url VARCHAR;
ALTER TABLE RAW.TEAM_CONFEDERATION ADD COLUMN IF NOT EXISTS cross_check_match BOOLEAN;
