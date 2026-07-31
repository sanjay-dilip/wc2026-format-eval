-- went_to_et and neutral_site are NULL for 2026 rows: not derivable from
-- current RAW.MATCH columns (docs/decision_log.md, 2026-07-30 entry).
-- went_to_so IS derivable (a RAW.SHOOTOUT record exists or it doesn't)
-- and is populated correctly.
--
-- stage_id and venue_id are nullable (not NOT NULL) because Build 5's
-- historical comparison rows have neither: no verified stage/round or
-- venue-coordinate source exists for non-2026 tournaments in this
-- project - see docs/decision_log.md. Still NOT NULL-enforced for the
-- 2026 rows via the orphaned-FK check in src/core/build_core.py, just not
-- at the column-constraint level, since one column can't have a
-- conditional constraint.
CREATE TABLE IF NOT EXISTS CORE.FACT_MATCH (
    match_id NUMBER PRIMARY KEY,
    tournament_id NUMBER NOT NULL REFERENCES CORE.DIM_TOURNAMENT (tournament_id),
    date_id NUMBER NOT NULL REFERENCES CORE.DIM_DATE (date_id),
    stage_id NUMBER REFERENCES CORE.DIM_STAGE (stage_id),
    venue_id NUMBER REFERENCES CORE.DIM_VENUE (venue_id),
    home_team_id NUMBER NOT NULL REFERENCES CORE.DIM_TEAM (team_id),
    away_team_id NUMBER NOT NULL REFERENCES CORE.DIM_TEAM (team_id),
    home_score NUMBER NOT NULL,
    away_score NUMBER NOT NULL,
    went_to_et BOOLEAN,
    went_to_so BOOLEAN NOT NULL,
    so_winner_id NUMBER REFERENCES CORE.DIM_TEAM (team_id),
    neutral_site BOOLEAN
);

-- ALTER, not just CREATE ... IF NOT EXISTS, so this stays safe to re-run
-- against an account where the table already existed pre-Build-5 (no
-- tournament_id, stage_id/venue_id still NOT NULL) - same pattern as
-- issue #13's RAW.VENUE_COORDINATES extension.
ALTER TABLE CORE.FACT_MATCH ADD COLUMN IF NOT EXISTS tournament_id NUMBER;
ALTER TABLE CORE.FACT_MATCH ALTER COLUMN stage_id DROP NOT NULL;
ALTER TABLE CORE.FACT_MATCH ALTER COLUMN venue_id DROP NOT NULL;
