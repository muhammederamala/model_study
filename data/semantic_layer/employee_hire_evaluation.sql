-- db_id: employee_hire_evaluation
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
-- Usage patterns mined from real questions follow at the bottom.
CREATE TABLE employee (  -- 10 rows
  Employee_ID NUMBER PRIMARY KEY,  -- employee id
  Name TEXT,  -- values: 'George Chuter', 'Lee Mears', 'Mark Regan', 'Jason Hobson', 'Tim Payne', 'Andrew Sheridan', 'Matt Stevens', 'Phil Vickery', 'Steve Borthwick', 'Louis Deacon'
  Age NUMBER,  -- range: 23 to 43
  City TEXT  -- values: 'Bristol', 'Bath', 'Wasps', 'Sale', 'Leicester'
);
CREATE TABLE shop (  -- 9 rows
  Shop_ID NUMBER PRIMARY KEY,  -- shop id
  Name TEXT,  -- values: 'FC Haka', 'HJK', 'FC Honka', 'FC Inter', 'FF Jaro', 'FC KooTeePee', 'KuPS', 'FC Lahti', 'IFK Mariehamn'
  Location TEXT,  -- values: 'Valkeakoski', 'Helsinki', 'Espoo', 'Turku', 'Jakobstad', 'Kotka', 'Kuopio', 'Lahti', 'Mariehamn'
  District TEXT,  -- values: 'Tehtaan kenttä', 'Finnair Stadium', 'Tapiolan Urheilupuisto', 'Veritas Stadion', 'Jakobstads Centralplan', 'Arto Tolsa Areena', 'Magnum Areena', 'Lahden Stadion', 'Wiklöf Holding Arena'
  Number_products NUMBER,  -- number products | range: 1600 to 15000
  Manager_name TEXT  -- manager name | values: 'Olli Huttunen', 'Antti Muurinen', 'Mika Lehkosuo', 'Job Dragtsma', 'Mika Laurikainen', 'Tommi Kautonen', 'Kai Nyyssönen', 'Ilkka Mäkelä', 'Pekka Lyyski'
);
CREATE TABLE hiring (  -- 7 rows
  Shop_ID NUMBER,  -- shop id | FK -> shop.Shop_ID
  Employee_ID NUMBER PRIMARY KEY,  -- employee id | FK -> employee.Employee_ID
  Start_from TEXT,  -- start from | values: '2009', '2003', '2011', '2012', '2013', '2010', '2008'
  Is_full_time OTHERS  -- is full time
);
CREATE TABLE evaluation (  -- 6 rows
  Employee_ID TEXT PRIMARY KEY,  -- employee id | FK -> employee.Employee_ID | TYPE MISMATCH: this col is TEXT, target is NUMBER (no CAST needed in SQLite, but be aware) | values: '1', '10', '2', '4', '7'
  Year_awarded TEXT,  -- year awarded | values: '2011', '2016', '2015', '2017', '2018'
  Bonus NUMBER  -- range: 2900 to 4000
);

-- ============================================================
-- USAGE PATTERNS for employee_hire_evaluation
-- Mined from 38 real analyst questions against this database.
-- Heuristic (regex-derived, not a SQL parser) — treat as guidance, not rules.
-- ============================================================
-- Most common join paths (8 of 38 questions join at least two tables):
--     4 questions:  employee.employee_id = evaluation.employee_id
--     4 questions:  hiring.shop_id = shop.shop_id
-- Metrics this database is usually asked for:
--    14 questions:  COUNT(*)  (plain row counts are the single most common ask)
--     2 questions:  MIN(number_products)
--     2 questions:  MAX(number_products)
--     2 questions:  AVG(number_products)
--     2 questions:  SUM(bonus)
--     2 questions:  COUNT(location)
-- Phrasing -> SQL constructs seen in this database's questions:
--   'how many' / 'number of' -> COUNT
--   'average' / 'mean' -> AVG
--   'for each' / 'per <thing>' / 'by <thing>' -> GROUP BY
--   'most' / 'highest' / 'largest' / 'top' -> ORDER BY ... DESC
--   'the single most/least ...' -> ORDER BY ... LIMIT 1
--   'never' / 'without any' / 'that do not' -> NOT IN / EXCEPT
--   'both X and Y' -> INTERSECT
--   'more than the average' / comparisons to an aggregate -> subquery