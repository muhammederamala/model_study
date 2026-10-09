-- db_id: pets_1
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
-- Usage patterns mined from real questions follow at the bottom.
CREATE TABLE Student (  -- 34 rows
  StuID NUMBER PRIMARY KEY,  -- stu id
  LName TEXT,
  Fname TEXT,
  Age NUMBER,  -- range: 16 to 27
  Sex TEXT,  -- values: 'F', 'M'
  Major NUMBER,  -- range: 50 to 600
  Advisor NUMBER,  -- range: 1121 to 9172
  city_code TEXT  -- city code
);
CREATE TABLE Has_Pet (  -- 3 rows
  StuID NUMBER,  -- stu id | FK -> Student.StuID
  PetID NUMBER  -- pet id | FK -> Pets.PetID
);
CREATE TABLE Pets (  -- 3 rows
  PetID NUMBER PRIMARY KEY,  -- pet id
  PetType TEXT,  -- pet type | values: 'cat', 'dog'
  pet_age NUMBER,  -- pet age | range: 1 to 3
  weight NUMBER  -- range: 9.3 to 13.4
);

-- ============================================================
-- USAGE PATTERNS for pets_1
-- Mined from 42 real analyst questions against this database.
-- Heuristic (regex-derived, not a SQL parser) — treat as guidance, not rules.
-- ============================================================
-- Most common join paths (24 of 42 questions join at least two tables):
--    24 questions:  has_pet.stuid = student.stuid
--    14 questions:  has_pet.petid = pets.petid
-- Metrics this database is usually asked for:
--    10 questions:  COUNT(*)  (plain row counts are the single most common ask)
--     2 questions:  MAX(weight)
--     2 questions:  COUNT(pettype)
--     2 questions:  AVG(pet_age)
--     2 questions:  MAX(pet_age)
--     2 questions:  AVG(weight)
--     2 questions:  AVG(age)
-- Phrasing -> SQL constructs seen in this database's questions:
--   'how many' / 'number of' -> COUNT
--   'average' / 'mean' -> AVG
--   'for each' / 'per <thing>' / 'by <thing>' -> GROUP BY
--   'never' / 'without any' / 'that do not' -> NOT IN / EXCEPT
--   'both X and Y' -> INTERSECT
--   'more than the average' / comparisons to an aggregate -> subquery