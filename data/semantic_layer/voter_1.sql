-- db_id: voter_1
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
-- Usage patterns mined from real questions follow at the bottom.
CREATE TABLE AREA_CODE_STATE (  -- 305 rows
  area_code NUMBER PRIMARY KEY,  -- area code
  state TEXT
);
CREATE TABLE CONTESTANTS (  -- 11 rows
  contestant_number NUMBER PRIMARY KEY,  -- contestant number
  contestant_name TEXT  -- contestant name | values: 'Edwina Burnam', 'Tabatha Gehling', 'Kelly Clauss', 'Jessie Alloway', 'Alana Bregman', 'Jessie Eichman', 'Allie Rogalski', 'Nita Coster', 'Kurt Walser', 'Ericka Dieter', 'Loraine NygrenTania Mattioli'
);
CREATE TABLE VOTES (  -- 4 rows
  vote_id NUMBER PRIMARY KEY,  -- vote id
  phone_number NUMBER,  -- phone number | range: 5112677315 to 7182887233
  state TEXT,  -- FK -> AREA_CODE_STATE.state | JOINS BY NON-PRIMARY-KEY COLUMN (target is not AREA_CODE_STATE's own primary key) | values: 'NY', 'CA', 'NJ\n'
  contestant_number NUMBER,  -- contestant number | FK -> CONTESTANTS.contestant_number | range: 2 to 5
  created TIME
);

-- ============================================================
-- USAGE PATTERNS for voter_1
-- Mined from 15 real analyst questions against this database.
-- Heuristic (regex-derived, not a SQL parser) — treat as guidance, not rules.
-- ============================================================
-- Most common join paths (5 of 15 questions join at least two tables):
--     4 questions:  contestants.contestant_number = votes.contestant_number
--     2 questions:  area_code_state.state = votes.state
-- Metrics this database is usually asked for:
--     6 questions:  COUNT(*)  (plain row counts are the single most common ask)
--     1 questions:  MAX(area_code)
--     1 questions:  MIN(area_code)
--     1 questions:  MAX(created)
-- Phrasing -> SQL constructs seen in this database's questions:
--   'how many' / 'number of' -> COUNT
--   'for each' / 'per <thing>' / 'by <thing>' -> GROUP BY
--   'most' / 'highest' / 'largest' / 'top' -> ORDER BY ... DESC
--   'the single most/least ...' -> ORDER BY ... LIMIT 1
--   'never' / 'without any' / 'that do not' -> NOT IN / EXCEPT
--   'both X and Y' -> INTERSECT
--   'more than the average' / comparisons to an aggregate -> subquery