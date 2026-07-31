-- Grain: one row per (team, tournament) - NOT a dim_team column. A
-- returning team (e.g. Brazil, in all 3 tournaments this project
-- compares) has a genuinely different FIFA ranking each time, so ranking
-- is tournament-relative, not team-invariant. dim_team.fifa_ranking (the
-- Build 1-era design, back when only 2026 existed) is superseded by this
-- table - see docs/decision_log.md, Build 6 entry, for why that column is
-- left NULL rather than populated with a single ambiguous snapshot.
-- fifa_ranking is nullable: teams not yet determined at their
-- tournament's ranking-snapshot date have no value (documented gap, not a
-- missing load - see RAW.FIFA_RANKING_SNAPSHOT).
CREATE TABLE IF NOT EXISTS CORE.TEAM_TOURNAMENT_RANKING (
    team_id NUMBER NOT NULL REFERENCES CORE.DIM_TEAM (team_id),
    tournament_id NUMBER NOT NULL REFERENCES CORE.DIM_TOURNAMENT (tournament_id),
    fifa_ranking NUMBER,
    ranking_as_of_date DATE,
    PRIMARY KEY (team_id, tournament_id)
);
