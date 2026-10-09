-- db_id: flight_2
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
-- Usage patterns mined from real questions follow at the bottom.
CREATE TABLE airlines (  -- 12 rows
  uid NUMBER PRIMARY KEY,
  Airline TEXT,  -- values: 'United Airlines', 'US Airways', 'Delta Airlines', 'Southwest Airlines', 'American Airlines', 'Northwest Airlines', 'Continental Airlines', 'JetBlue Airways', 'Frontier Airlines', 'AirTran Airways', 'Allegiant Air', 'Virgin America'
  Abbreviation TEXT,  -- values: 'UAL', 'USAir', 'Delta', 'Southwest', 'American', 'Northwest', 'Continental', 'JetBlue', 'Frontier', 'AirTran', 'Allegiant', 'Virgin'
  Country TEXT  -- values: 'USA'
);
CREATE TABLE airports (  -- 100 rows
  City TEXT,
  AirportCode TEXT PRIMARY KEY,  -- airport code
  AirportName TEXT,  -- airport name
  Country TEXT,  -- values: 'United States '
  CountryAbbrev TEXT  -- country abbrev | values: 'US ', 'US'
);
CREATE TABLE flights (  -- 1200 rows
  Airline NUMBER PRIMARY KEY,
  FlightNo NUMBER,  -- flight no | range: 2 to 1535
  SourceAirport TEXT,  -- source airport | FK -> airports.AirportCode
  DestAirport TEXT  -- dest airport | FK -> airports.AirportCode
);

-- ============================================================
-- USAGE PATTERNS for flight_2
-- Mined from 80 real analyst questions against this database.
-- Heuristic (regex-derived, not a SQL parser) — treat as guidance, not rules.
-- ============================================================
-- Most common join paths (46 of 80 questions join at least two tables):
--    26 questions:  airlines.uid = flights.airline
--    16 questions:  airports.airportcode = flights.destairport
--    12 questions:  airports.airportcode = flights.sourceairport
-- Metrics this database is usually asked for:
--    44 questions:  COUNT(*)  (plain row counts are the single most common ask)
-- Phrasing -> SQL constructs seen in this database's questions:
--   'how many' / 'number of' -> COUNT
--   'for each' / 'per <thing>' / 'by <thing>' -> GROUP BY
--   'most' / 'highest' / 'largest' / 'top' -> ORDER BY ... DESC
--   'the single most/least ...' -> ORDER BY ... LIMIT 1
--   'never' / 'without any' / 'that do not' -> NOT IN / EXCEPT
--   'both X and Y' -> INTERSECT
--   'more than the average' / comparisons to an aggregate -> subquery