SELECT m.match_date, m.home_team, m.away_team,
       'group mismatch: home_group=' || COALESCE(hg.group_letter, 'NULL') ||
       ' away_group=' || COALESCE(ag.group_letter, 'NULL') ||
       ' row.group_letter=' || COALESCE(m.group_letter, 'NULL') AS detail
FROM RAW.MATCH m
LEFT JOIN RAW.GROUP_DRAW hg ON hg.team = m.home_team
LEFT JOIN RAW.GROUP_DRAW ag ON ag.team = m.away_team
WHERE m.is_knockout = FALSE
  AND NOT (hg.group_letter = ag.group_letter AND ag.group_letter = m.group_letter)
