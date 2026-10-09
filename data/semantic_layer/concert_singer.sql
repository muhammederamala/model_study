-- db_id: concert_singer
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
-- Usage patterns mined from real questions follow at the bottom.
CREATE TABLE stadium (  -- 9 rows
  Stadium_ID NUMBER PRIMARY KEY,  -- stadium id
  Location TEXT,  -- values: 'Raith Rovers', 'Ayr United', 'East Fife', "Queen's Park", 'Stirling Albion', 'Arbroath', 'Alloa Athletic', 'Peterhead', 'Brechin City'
  Name TEXT,  -- values: "Stark's Park", 'Somerset Park', 'Bayview Stadium', 'Hampden Park', 'Forthbank Stadium', 'Gayfield Park', 'Recreation Park', 'Balmoor', 'Glebe Park'
  Capacity NUMBER,  -- range: 2000 to 52500
  Highest NUMBER,  -- range: 780 to 4812
  Lowest NUMBER,  -- range: 315 to 1294
  Average NUMBER  -- range: 552 to 2106
);
CREATE TABLE singer (  -- 6 rows
  Singer_ID NUMBER PRIMARY KEY,  -- singer id
  Name TEXT,  -- values: 'Joe Sharp', 'Timbaland', 'Justin Brown', 'Rose White', 'John Nizinik', 'Tribal King'
  Country TEXT,  -- values: 'Netherlands', 'United States', 'France'
  Song_Name TEXT,  -- song name | values: 'You', 'Dangerous', 'Hey Oh', 'Sun', 'Gentleman', 'Love'
  Song_release_year TEXT,  -- song release year | values: '1992', '2008', '2013', '2003', '2014', '2016'
  Age NUMBER,  -- range: 25 to 52
  Is_male OTHERS  -- is male
);
CREATE TABLE concert (  -- 6 rows
  concert_ID NUMBER PRIMARY KEY,  -- concert id
  concert_Name TEXT,  -- concert name | values: 'Auditions', 'Super bootcamp', 'Home Visits', 'Week 1', 'Week 2'
  Theme TEXT,  -- values: 'Free choice', 'Free choice 2', 'Bleeding Love', 'Wide Awake', 'Happy Tonight', 'Party All Night'
  Stadium_ID TEXT,  -- stadium id | FK -> stadium.Stadium_ID | TYPE MISMATCH: this col is TEXT, target is NUMBER (no CAST needed in SQLite, but be aware) | values: '1', '2', '10', '9', '7'
  Year TEXT  -- values: '2014', '2015'
);
CREATE TABLE singer_in_concert (  -- 10 rows
  concert_ID NUMBER PRIMARY KEY,  -- concert id | FK -> concert.concert_ID
  Singer_ID TEXT  -- singer id | FK -> singer.Singer_ID | TYPE MISMATCH: this col is TEXT, target is NUMBER (no CAST needed in SQLite, but be aware) | values: '2', '3', '5', '6', '4'
);

-- ============================================================
-- USAGE PATTERNS for concert_singer
-- Mined from 45 real analyst questions against this database.
-- Heuristic (regex-derived, not a SQL parser) — treat as guidance, not rules.
-- ============================================================
-- Most common join paths (14 of 45 questions join at least two tables):
--     8 questions:  concert.stadium_id = stadium.stadium_id
--     4 questions:  concert.concert_id = singer_in_concert.concert_id
--     4 questions:  singer.singer_id = singer_in_concert.singer_id
-- Metrics this database is usually asked for:
--    18 questions:  COUNT(*)  (plain row counts are the single most common ask)
--     4 questions:  AVG(age)
--     2 questions:  MIN(age)
--     2 questions:  MAX(age)
--     2 questions:  MAX(capacity)
--     1 questions:  AVG(capacity)
-- Phrasing -> SQL constructs seen in this database's questions:
--   'how many' / 'number of' -> COUNT
--   'average' / 'mean' -> AVG
--   'for each' / 'per <thing>' / 'by <thing>' -> GROUP BY
--   'most' / 'highest' / 'largest' / 'top' -> ORDER BY ... DESC
--   'the single most/least ...' -> ORDER BY ... LIMIT 1
--   'never' / 'without any' / 'that do not' -> NOT IN / EXCEPT
--   'both X and Y' -> INTERSECT
--   'more than the average' / comparisons to an aggregate -> subquery