-- db_id: pets_1
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
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