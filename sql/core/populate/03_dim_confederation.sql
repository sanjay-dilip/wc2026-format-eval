INSERT INTO CORE.DIM_CONFEDERATION (confederation_id, confederation_name)
SELECT ROW_NUMBER() OVER (ORDER BY confederation_name), confederation_name
FROM (SELECT DISTINCT confederation_name FROM RAW.TEAM_CONFEDERATION)
