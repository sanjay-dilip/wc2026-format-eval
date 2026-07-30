-- went_to_et and neutral_site are NULL for all rows: not derivable from
-- current RAW.MATCH columns (docs/decision_log.md, 2026-07-30 entry).
-- went_to_so IS derivable (a RAW.SHOOTOUT record exists or it doesn't)
-- and is populated correctly.
CREATE TABLE IF NOT EXISTS CORE.FACT_MATCH (
    match_id NUMBER PRIMARY KEY,
    date_id NUMBER NOT NULL REFERENCES CORE.DIM_DATE (date_id),
    stage_id NUMBER NOT NULL REFERENCES CORE.DIM_STAGE (stage_id),
    venue_id NUMBER NOT NULL REFERENCES CORE.DIM_VENUE (venue_id),
    home_team_id NUMBER NOT NULL REFERENCES CORE.DIM_TEAM (team_id),
    away_team_id NUMBER NOT NULL REFERENCES CORE.DIM_TEAM (team_id),
    home_score NUMBER NOT NULL,
    away_score NUMBER NOT NULL,
    went_to_et BOOLEAN,
    went_to_so BOOLEAN NOT NULL,
    so_winner_id NUMBER REFERENCES CORE.DIM_TEAM (team_id),
    neutral_site BOOLEAN
);
