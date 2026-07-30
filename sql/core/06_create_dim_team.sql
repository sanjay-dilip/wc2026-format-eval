-- fifa_ranking is NULL until Build 6 closes the rankings gap - not a
-- placeholder guess (docs/architecture.md).
CREATE TABLE IF NOT EXISTS CORE.DIM_TEAM (
    team_id NUMBER PRIMARY KEY,
    team_name VARCHAR NOT NULL,
    group_id NUMBER REFERENCES CORE.DIM_GROUP (group_id),
    confederation_id NUMBER REFERENCES CORE.DIM_CONFEDERATION (confederation_id),
    fifa_ranking NUMBER
);
