-- Mirrors data/raw/wc_fifa_ranking_snapshots.csv column-for-column: one
-- row per team per tournament (2026, 2022, 1994), each team's official
-- FIFA World Ranking as of that tournament's own draw/qualification date
-- - not a continuous historical time series (Build 6, docs/decision_log.md
-- explains why). fifa_ranking was originally NULL for 9 teams not yet
-- determined at their tournament's snapshot date's seeding table (2026's
-- 6 late playoff qualifiers, 2022's 3) - issue #39's second-source
-- cross-check found real ranking values existed for all 9 on a general
-- FIFA ranking archive, not tied to World Cup seeding, and backfilled
-- them (see docs/decision_log.md, issue #39 entry). second_source_url and
-- cross_check_status document that per row.
CREATE TABLE IF NOT EXISTS RAW.FIFA_RANKING_SNAPSHOT (
    tournament_year NUMBER,
    team VARCHAR,
    fifa_ranking NUMBER,
    ranking_as_of_date DATE,
    source_url VARCHAR,
    second_source_url VARCHAR,
    cross_check_status VARCHAR
);

-- ALTER, not just CREATE ... IF NOT EXISTS, so this stays safe to re-run
-- against an account where the table already existed pre-issue-#39
-- (2 columns narrower).
ALTER TABLE RAW.FIFA_RANKING_SNAPSHOT ADD COLUMN IF NOT EXISTS second_source_url VARCHAR;
ALTER TABLE RAW.FIFA_RANKING_SNAPSHOT ADD COLUMN IF NOT EXISTS cross_check_status VARCHAR;
