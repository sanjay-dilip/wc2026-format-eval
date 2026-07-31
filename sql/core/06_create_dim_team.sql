-- fifa_ranking stays permanently NULL, not populated by Build 6 as
-- originally planned in docs/architecture.md: a single team-level column
-- can't hold a value that's genuinely different per tournament for a
-- returning team (e.g. Brazil's rank differs across the 2026/2022/1994
-- comparison set). CORE.TEAM_TOURNAMENT_RANKING (grain: team x
-- tournament) supersedes this column - see docs/decision_log.md, Build 6
-- entry. Column left in place, not dropped, since dropping it is outside
-- this change's scope and it costs nothing to leave unused.
CREATE TABLE IF NOT EXISTS CORE.DIM_TEAM (
    team_id NUMBER PRIMARY KEY,
    team_name VARCHAR NOT NULL,
    group_id NUMBER REFERENCES CORE.DIM_GROUP (group_id),
    confederation_id NUMBER REFERENCES CORE.DIM_CONFEDERATION (confederation_id),
    fifa_ranking NUMBER
);
