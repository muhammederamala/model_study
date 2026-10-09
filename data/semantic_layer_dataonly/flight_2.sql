-- db_id: flight_2
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
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