-- db_id: battle_death
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
-- Usage patterns mined from real questions follow at the bottom.
CREATE TABLE battle (  -- 8 rows
  id NUMBER PRIMARY KEY,
  name TEXT,  -- values: 'Battle of Adrianople', 'Battle of Serres', 'Battle of Rusion', 'Battle of Rodosto', 'Battle of Messinopolis', 'Battle of Boruy', 'Battle of Philippopolis', 'Siege of Constantinople'
  date TEXT,  -- values: '14 April 1205', 'June 1205', '31 January 1206', 'February 1206', '4 September 1207', '31 June 1208', '1235'
  bulgarian_commander TEXT,  -- bulgarian commander | values: 'Kaloyan', 'Unknown', 'Boril', 'Ivan Asen II'
  latin_commander TEXT,  -- latin commander | values: 'Baldwin I', 'Unknown', 'Thierry de Termond', 'Boniface of Montferrat', 'Henry I', 'John of Brienne'
  result TEXT  -- values: 'Bulgarian victory', 'Latin victory', 'Two Year Truce'
);
CREATE TABLE ship (  -- 7 rows
  lost_in_battle NUMBER,  -- lost in battle | FK -> battle.id | range: 4 to 8
  id NUMBER PRIMARY KEY,
  name TEXT,  -- values: 'Lettice', 'Bon Accord', 'Mary', 'HMS Avon', 'Three Brothers', 'Bacchus', 'HMS Atalanta'
  tonnage TEXT,  -- values: 't', '391', '225'
  ship_type TEXT,  -- ship type | values: 'Brig', '18-gun Brig', '8 gun Brig'
  location TEXT,  -- values: 'English Channel', 'SW Approaches', 'Mid-Atlantic'
  disposition_of_ship TEXT  -- disposition of ship | values: 'Captured', 'Wrecked', 'Scuttled', 'Sank'
);
CREATE TABLE death (  -- 13 rows
  caused_by_ship_id NUMBER,  -- caused by ship id | FK -> ship.id
  id NUMBER PRIMARY KEY,
  note TEXT,  -- values: 'Dantewada, Chhattisgarh', 'Erraboru, Chhattisgarh', 'East Champaran, Bihar', 'Gajapati, Odisha', 'Sundargarh, Odisha', 'Kanker, Chhattisgarh', 'WestMidnapore, West Bengal', 'Bastar, Chattisgarh', 'Bokaro, Jharkhand'
  killed NUMBER,  -- range: 0 to 29
  injured NUMBER  -- range: 0 to 9
);

-- ============================================================
-- USAGE PATTERNS for battle_death
-- Mined from 16 real analyst questions against this database.
-- Heuristic (regex-derived, not a SQL parser) — treat as guidance, not rules.
-- ============================================================
-- Most common join paths (6 of 16 questions join at least two tables):
--     4 questions:  battle.id = ship.lost_in_battle
--     3 questions:  death.caused_by_ship_id = ship.id
-- Metrics this database is usually asked for:
--     3 questions:  COUNT(*)  (plain row counts are the single most common ask)
--     1 questions:  MAX(killed)
--     1 questions:  MIN(killed)
--     1 questions:  AVG(injured)
--     1 questions:  SUM(death.killed)
--     1 questions:  COUNT(result)
-- Phrasing -> SQL constructs seen in this database's questions:
--   'how many' / 'number of' -> COUNT
--   'average' / 'mean' -> AVG
--   'for each' / 'per <thing>' / 'by <thing>' -> GROUP BY
--   'most' / 'highest' / 'largest' / 'top' -> ORDER BY ... DESC
--   'the single most/least ...' -> ORDER BY ... LIMIT 1
--   'never' / 'without any' / 'that do not' -> NOT IN / EXCEPT
--   'both X and Y' -> INTERSECT
--   'more than the average' / comparisons to an aggregate -> subquery