-- Consumes RAW.MATCH_STREAM into CORE.FACT_MATCH incrementally - no
-- truncate, unlike every populate/ query in this directory. Two branches,
-- both scoped to Build 8's stated work items only (new-match arrival,
-- correction) - row deletion is explicitly out of scope, not handled:
--
--   1. Corrections (METADATA$ISUPDATE = TRUE): UPDATE the matching
--      CORE.FACT_MATCH row's scores in place, keyed on the same natural
--      key (tournament_id, date_id, home_team_id, away_team_id) the
--      dimensional model already uses everywhere else.
--   2. New matches (METADATA$ISUPDATE = FALSE, ACTION = 'INSERT'):
--      INSERT with match_id = current MAX(match_id) + ROW_NUMBER() over
--      the new rows - same pattern already used by
--      sql/core/populate/10_fact_match_historical.sql to append the
--      historical block without colliding with 07_fact_match.sql's IDs.
--      This assignment is only guaranteed to match what a from-scratch
--      full rebuild's global ROW_NUMBER() would produce if the new row's
--      (match_date, home_team, away_team) sort key is not earlier than
--      every existing 2026 row's - true for a genuinely new match
--      arriving after the tournament's last already-loaded date, the
--      only scenario this build's "new-match arrival" work item actually
--      describes. Documented here rather than silently assumed - see
--      docs/decision_log.md, Build 8 entry, for why the demo's
--      hash-comparison script compares by natural key/business columns,
--      not raw match_id, to stay correct even when a full rebuild
--      renumbers the trailing historical block after such an insert.
--
-- Both statements read from RAW.MATCH_STREAM inside one explicit
-- transaction, so the stream offset only advances once, after both have
-- run against the same consistent change set - the documented pattern for
-- consuming one stream across multiple DML statements.
CREATE OR REPLACE PROCEDURE CORE.SP_APPLY_MATCH_STREAM()
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    BEGIN TRANSACTION;

    UPDATE CORE.FACT_MATCH t
    SET t.home_score = src.home_score, t.away_score = src.away_score
    FROM (
        SELECT
            d.date_id, ht.team_id AS home_team_id, at.team_id AS away_team_id,
            tour.tournament_id, s.home_score, s.away_score
        FROM RAW.MATCH_STREAM s
        JOIN CORE.DIM_DATE d ON d.full_date = s.match_date
        JOIN CORE.DIM_TEAM ht ON ht.team_name = s.home_team
        JOIN CORE.DIM_TEAM at ON at.team_name = s.away_team
        JOIN CORE.DIM_TOURNAMENT tour ON tour.tournament_year = 2026
        WHERE s.METADATA$ACTION = 'INSERT' AND s.METADATA$ISUPDATE = TRUE
    ) src
    WHERE t.date_id = src.date_id
      AND t.home_team_id = src.home_team_id
      AND t.away_team_id = src.away_team_id
      AND t.tournament_id = src.tournament_id;

    LET rows_corrected INTEGER := SQLROWCOUNT;

    INSERT INTO CORE.FACT_MATCH (
        match_id, tournament_id, date_id, stage_id, venue_id, home_team_id, away_team_id,
        home_score, away_score, went_to_et, went_to_so, so_winner_id, neutral_site
    )
    SELECT
        (SELECT COALESCE(MAX(match_id), 0) FROM CORE.FACT_MATCH)
            + ROW_NUMBER() OVER (ORDER BY s.match_date, s.home_team, s.away_team),
        tour.tournament_id,
        d.date_id,
        st.stage_id,
        v.venue_id,
        ht.team_id,
        at.team_id,
        s.home_score,
        s.away_score,
        NULL,
        sh.match_date IS NOT NULL,
        so.team_id,
        NULL
    FROM RAW.MATCH_STREAM s
    JOIN CORE.DIM_DATE d ON d.full_date = s.match_date
    JOIN CORE.DIM_STAGE st ON st.stage_name = s.stage
    JOIN CORE.DIM_VENUE v
        ON v.city = CASE WHEN s.venue_city = 'Dallas' THEN 'Arlington' ELSE s.venue_city END
       AND v.country = s.venue_country
    JOIN CORE.DIM_TEAM ht ON ht.team_name = s.home_team
    JOIN CORE.DIM_TEAM at ON at.team_name = s.away_team
    JOIN CORE.DIM_TOURNAMENT tour ON tour.tournament_year = 2026
    LEFT JOIN RAW.SHOOTOUT sh
        ON sh.match_date = s.match_date AND sh.home_team = s.home_team AND sh.away_team = s.away_team
    LEFT JOIN CORE.DIM_TEAM so ON so.team_name = sh.winner
    WHERE s.METADATA$ACTION = 'INSERT' AND s.METADATA$ISUPDATE = FALSE;

    LET rows_inserted INTEGER := SQLROWCOUNT;

    COMMIT;

    RETURN 'corrected=' || rows_corrected || ' inserted=' || rows_inserted;
END;
$$
