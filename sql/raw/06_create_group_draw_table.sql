-- Mirrors data/raw/wc2026_group_draw.csv column-for-column: the 48-team
-- roster/group crosswalk, needed in the warehouse so VALIDATION checks can
-- run against it directly instead of only against the local file. Plus a
-- second-source cross-check per row (see docs/decision_log.md, issue #33
-- entry).
CREATE TABLE IF NOT EXISTS RAW.GROUP_DRAW (
    team VARCHAR,
    group_letter VARCHAR,
    second_source_url VARCHAR,
    cross_check_match BOOLEAN
);

-- ALTER, not just CREATE ... IF NOT EXISTS, so this stays safe to re-run
-- against an account where the table already existed pre-issue-#33
-- (2 columns narrower).
ALTER TABLE RAW.GROUP_DRAW ADD COLUMN IF NOT EXISTS second_source_url VARCHAR;
ALTER TABLE RAW.GROUP_DRAW ADD COLUMN IF NOT EXISTS cross_check_match BOOLEAN;
