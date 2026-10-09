-- db_id: poker_player
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
-- Usage patterns mined from real questions follow at the bottom.
CREATE TABLE poker_player (  -- 5 rows
  Poker_Player_ID NUMBER PRIMARY KEY,  -- poker player id
  People_ID NUMBER,  -- people id | FK -> people.People_ID
  Final_Table_Made NUMBER,  -- final table made | range: 10 to 42
  Best_Finish NUMBER,  -- best finish | range: 1 to 3
  Money_Rank NUMBER,  -- money rank | range: 58 to 166
  Earnings NUMBER  -- range: 104871 to 596462
);
CREATE TABLE people (  -- 7 rows
  People_ID NUMBER PRIMARY KEY,  -- people id
  Nationality TEXT,  -- values: 'Russia', 'Bulgaria'
  Name TEXT,  -- values: 'Aleksey Ostapenko', 'Teodor Salparov', 'Roman Bragin', 'Sergey Grankin', 'Yevgeni Sivozhelez', 'Maksim Botin', 'Semen Poltavskiy'
  Birth_Date TEXT,  -- birth date | values: 'May 26, 1986', 'August 16, 1982', 'April 17, 1987', 'January 22, 1987', 'August 8, 1986', 'July 14, 1983', 'February 8, 1981'
  Height NUMBER  -- range: 182 to 207
);

-- ============================================================
-- USAGE PATTERNS for poker_player
-- Mined from 40 real analyst questions against this database.
-- Heuristic (regex-derived, not a SQL parser) — treat as guidance, not rules.
-- ============================================================
-- Most common join paths (14 of 40 questions join at least two tables):
--    14 questions:  people.people_id = poker_player.people_id
-- Metrics this database is usually asked for:
--     8 questions:  COUNT(*)  (plain row counts are the single most common ask)
--     2 questions:  AVG(earnings)
--     2 questions:  MAX(final_table_made)
--     2 questions:  AVG(poker_player.earnings)
--     2 questions:  COUNT(nationality)
-- Phrasing -> SQL constructs seen in this database's questions:
--   'how many' / 'number of' -> COUNT
--   'average' / 'mean' -> AVG
--   'for each' / 'per <thing>' / 'by <thing>' -> GROUP BY
--   'most' / 'highest' / 'largest' / 'top' -> ORDER BY ... DESC
--   'the single most/least ...' -> ORDER BY ... LIMIT 1
--   'never' / 'without any' / 'that do not' -> NOT IN / EXCEPT
--   'more than the average' / comparisons to an aggregate -> subquery