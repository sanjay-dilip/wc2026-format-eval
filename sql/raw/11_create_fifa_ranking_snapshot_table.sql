-- Mirrors data/raw/wc_fifa_ranking_snapshots.csv column-for-column: one
-- row per team per tournament (2026, 2022, 1994), each team's official
-- FIFA World Ranking as of that tournament's own draw/qualification date
-- - not a continuous historical time series (Build 6, docs/decision_log.md
-- explains why). fifa_ranking is NULL for teams not yet determined at
-- their tournament's snapshot date (2026's 6 late playoff qualifiers,
-- 2022's 3) - a genuine, documented gap, not a missing load.
CREATE TABLE IF NOT EXISTS RAW.FIFA_RANKING_SNAPSHOT (
    tournament_year NUMBER,
    team VARCHAR,
    fifa_ranking NUMBER,
    ranking_as_of_date DATE,
    source_url VARCHAR
);
