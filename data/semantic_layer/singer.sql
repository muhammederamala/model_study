-- db_id: singer
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
-- Usage patterns mined from real questions follow at the bottom.
CREATE TABLE singer (  -- 8 rows
  Singer_ID NUMBER PRIMARY KEY,  -- singer id
  Name TEXT,  -- values: 'Liliane Bettencourt', 'Christy Walton', 'Alice Walton', 'Iris Fontbona', 'Jacqueline Mars', 'Gina Rinehart', 'Susanne Klatten', 'Abigail Johnson'
  Birth_Year NUMBER,  -- birth year | range: 1940 to 1962
  Net_Worth_Millions NUMBER,  -- net worth millions | range: 12.7 to 30
  Citizenship TEXT  -- values: 'France', 'United States', 'Chile', 'Australia', 'Germany'
);
CREATE TABLE song (  -- 8 rows
  Song_ID NUMBER PRIMARY KEY,  -- song id
  Title TEXT,  -- values: "Do They Know It's Christmas", "F**k It (I Don't Want You Back)", 'Cha Cha Slide', 'Call on Me', 'Yeah', 'All This Time', 'Left Outside Alone', 'Mysterious Girl'
  Singer_ID NUMBER,  -- singer id | FK -> singer.Singer_ID
  Sales NUMBER,  -- range: 261000 to 1094000
  Highest_Position NUMBER  -- highest position | range: 1 to 3
);

-- ============================================================
-- USAGE PATTERNS for singer
-- Mined from 30 real analyst questions against this database.
-- Heuristic (regex-derived, not a SQL parser) — treat as guidance, not rules.
-- ============================================================
-- Most common join paths (8 of 30 questions join at least two tables):
--     8 questions:  singer.singer_id = song.singer_id
-- Metrics this database is usually asked for:
--     8 questions:  COUNT(*)  (plain row counts are the single most common ask)
--     2 questions:  MAX(net_worth_millions)
--     2 questions:  SUM(song.sales)
-- Phrasing -> SQL constructs seen in this database's questions:
--   'how many' / 'number of' -> COUNT
--   'for each' / 'per <thing>' / 'by <thing>' -> GROUP BY
--   'most' / 'highest' / 'largest' / 'top' -> ORDER BY ... DESC
--   'the single most/least ...' -> ORDER BY ... LIMIT 1
--   'never' / 'without any' / 'that do not' -> NOT IN / EXCEPT
--   'both X and Y' -> INTERSECT
--   'more than the average' / comparisons to an aggregate -> subquery