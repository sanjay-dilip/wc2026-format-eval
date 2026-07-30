-- One row per team per match: distance traveled and rest days since that
-- team's previous match. distance_km/rest_days/previous_* are NULL for a
-- team's first match in the tournament - no previous match to compare
-- against. rest_days definition and the no-timezone-conversion rationale
-- are documented in docs/decision_log.md (2026-07-30 entry) - decided
-- before this table was populated, not after.
CREATE TABLE IF NOT EXISTS ANALYTICS.TEAM_TRAVEL_REST (
    row_id NUMBER AUTOINCREMENT PRIMARY KEY,
    team_id NUMBER NOT NULL REFERENCES CORE.DIM_TEAM (team_id),
    match_id NUMBER NOT NULL REFERENCES CORE.FACT_MATCH (match_id),
    match_date DATE NOT NULL,
    venue_id NUMBER NOT NULL REFERENCES CORE.DIM_VENUE (venue_id),
    previous_match_id NUMBER REFERENCES CORE.FACT_MATCH (match_id),
    previous_venue_id NUMBER REFERENCES CORE.DIM_VENUE (venue_id),
    previous_match_date DATE,
    distance_km FLOAT,
    rest_days NUMBER
);
