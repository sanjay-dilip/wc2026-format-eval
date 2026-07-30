-- Mirrors data/raw/wc2026_group_draw.csv column-for-column: the 48-team
-- roster/group crosswalk, needed in the warehouse so VALIDATION checks can
-- run against it directly instead of only against the local file.
CREATE TABLE IF NOT EXISTS RAW.GROUP_DRAW (
    team VARCHAR,
    group_letter VARCHAR
);
