-- db_id: car_1
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
CREATE TABLE continents (  -- 5 rows
  ContId NUMBER PRIMARY KEY,  -- cont id
  Continent TEXT  -- values: 'america', 'europe', 'asia', 'africa', 'australia'
);
CREATE TABLE countries (  -- 15 rows
  CountryId NUMBER PRIMARY KEY,  -- country id
  CountryName TEXT,  -- country name
  Continent NUMBER  -- FK -> continents.ContId | range: 1 to 5
);
CREATE TABLE car_makers (  -- 22 rows
  Id NUMBER PRIMARY KEY,
  Maker TEXT,
  FullName TEXT,  -- full name
  Country TEXT  -- FK -> countries.CountryId | TYPE MISMATCH: this col is TEXT, target is NUMBER (no CAST needed in SQLite, but be aware) | values: '1', '2', '3', '4', '5', '6', '7', '8'
);
CREATE TABLE model_list (  -- 36 rows
  ModelId NUMBER PRIMARY KEY,  -- model id
  Maker NUMBER,  -- FK -> car_makers.Id | range: 1 to 23
  Model TEXT
);
CREATE TABLE car_names (  -- 406 rows
  MakeId NUMBER PRIMARY KEY,  -- make id
  Model TEXT,  -- FK -> model_list.Model | JOINS BY NON-PRIMARY-KEY COLUMN (target is not model_list's own primary key)
  Make TEXT
);
CREATE TABLE cars_data (  -- 406 rows
  Id NUMBER PRIMARY KEY,  -- FK -> car_names.MakeId
  MPG TEXT,
  Cylinders NUMBER,  -- range: 3 to 8
  Edispl NUMBER,  -- range: 68 to 455
  Horsepower TEXT,
  Weight NUMBER,  -- range: 1613 to 5140
  Accelerate NUMBER,  -- range: 8 to 24.8
  Year NUMBER  -- range: 1970 to 1982
);