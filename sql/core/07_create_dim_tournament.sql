-- One row per tournament this project computes metrics for: 2026 plus the
-- Build 5 historical comparison baseline (2022, 1994). team_count is
-- computed from the actual matches loaded, not hardcoded, so it can't
-- silently drift from the data (docs/core/populate/09_dim_tournament.sql).
CREATE TABLE IF NOT EXISTS CORE.DIM_TOURNAMENT (
    tournament_id NUMBER PRIMARY KEY,
    tournament_year NUMBER NOT NULL,
    team_count NUMBER NOT NULL,
    format_label VARCHAR NOT NULL
);
