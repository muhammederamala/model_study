-- db_id: network_1
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
-- Usage patterns mined from real questions follow at the bottom.
CREATE TABLE Highschooler (  -- 16 rows
  ID NUMBER PRIMARY KEY,
  name TEXT,
  grade NUMBER  -- range: 9 to 12
);
CREATE TABLE Friend (  -- 20 rows
  student_id NUMBER PRIMARY KEY,  -- student id | FK -> Highschooler.ID
  friend_id NUMBER  -- friend id | FK -> Highschooler.ID
);
CREATE TABLE Likes (  -- 10 rows
  student_id NUMBER PRIMARY KEY,  -- student id | FK -> Highschooler.ID
  liked_id NUMBER  -- liked id | FK -> Highschooler.ID
);

-- ============================================================
-- USAGE PATTERNS for network_1
-- Mined from 56 real analyst questions against this database.
-- Heuristic (regex-derived, not a SQL parser) — treat as guidance, not rules.
-- ============================================================
-- Most common join paths (28 of 56 questions join at least two tables):
--    18 questions:  friend.student_id = highschooler.id
--    10 questions:  highschooler.id = likes.student_id
--     2 questions:  friend.friend_id = highschooler.id
--     2 questions:  highschooler.id = likes.liked_id
-- Metrics this database is usually asked for:
--    32 questions:  COUNT(*)  (plain row counts are the single most common ask)
--     2 questions:  AVG(grade)
--     2 questions:  MIN(grade)
-- Phrasing -> SQL constructs seen in this database's questions:
--   'how many' / 'number of' -> COUNT
--   'average' / 'mean' -> AVG
--   'for each' / 'per <thing>' / 'by <thing>' -> GROUP BY
--   'most' / 'highest' / 'largest' / 'top' -> ORDER BY ... DESC
--   'the single most/least ...' -> ORDER BY ... LIMIT 1
--   'never' / 'without any' / 'that do not' -> NOT IN / EXCEPT
--   'both X and Y' -> INTERSECT
--   'more than the average' / comparisons to an aggregate -> subquery