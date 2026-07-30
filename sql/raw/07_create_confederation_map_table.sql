-- Mirrors data/raw/wc2026_confederation_map.csv column-for-column: the
-- 48-team-to-confederation crosswalk, compiled per decision_log.md
-- (2026-07-30 entry), needed so dim_team/dim_confederation can be built
-- from warehouse data.
CREATE TABLE IF NOT EXISTS RAW.TEAM_CONFEDERATION (
    team VARCHAR,
    confederation_name VARCHAR
);
