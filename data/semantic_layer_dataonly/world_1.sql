-- db_id: world_1
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
CREATE TABLE city (  -- 4079 rows
  ID NUMBER PRIMARY KEY,
  Name TEXT,
  CountryCode TEXT,  -- country code | FK -> country.Code
  District TEXT,
  Population NUMBER  -- range: 42 to 10500000
);
CREATE TABLE sqlite_sequence (  -- 1 rows
  name TEXT,  -- values: 'city'
  seq TEXT  -- values: 4079
);
CREATE TABLE country (  -- 239 rows
  Code TEXT PRIMARY KEY,
  Name TEXT,
  Continent TEXT,  -- values: 'North America', 'Asia', 'Africa', 'Europe', 'South America', 'Oceania', 'Antarctica'
  Region TEXT,
  SurfaceArea NUMBER,  -- surface area | range: 0.4 to 17075400
  IndepYear NUMBER,  -- indep year | range: -1523 to 1994
  Population NUMBER,  -- range: 0 to 1277558000
  LifeExpectancy NUMBER,  -- life expectancy | range: 37.2 to 83.5
  GNP NUMBER,  -- range: 0 to 8510700
  GNPOld NUMBER,  -- range: 157 to 8110900
  LocalName TEXT,  -- local name
  GovernmentForm TEXT,  -- government form
  HeadOfState TEXT,  -- head of state
  Capital NUMBER,  -- range: 1 to 4074
  Code2 TEXT
);
CREATE TABLE countrylanguage (  -- 984 rows
  CountryCode TEXT PRIMARY KEY,  -- country code | FK -> country.Code
  Language TEXT,
  IsOfficial TEXT,  -- is official | values: 'T', 'F'
  Percentage NUMBER  -- range: 0 to 100
);