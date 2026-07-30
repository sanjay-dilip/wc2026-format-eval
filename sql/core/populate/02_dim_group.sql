INSERT INTO CORE.DIM_GROUP (group_id, group_letter)
SELECT ROW_NUMBER() OVER (ORDER BY group_letter), group_letter
FROM (SELECT DISTINCT group_letter FROM RAW.GROUP_DRAW)
