-- db_id: museum_visit
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
CREATE TABLE museum (  -- 8 rows
  Museum_ID NUMBER PRIMARY KEY,  -- museum id
  Name TEXT,  -- values: 'Plaza Museum', 'Capital Plaza Museum', 'Jefferson Development Museum', 'Willow Grande Museum', 'RiverPark Museum', 'Place Tower Museum', 'Central City District Residential Museum', 'ZirMed Gateway Museum'
  Num_of_Staff NUMBER,  -- num of staff | range: 12 to 62
  Open_Year TEXT  -- open year | values: '2000', '2012', '2010', '2011', '2008', '2009'
);
CREATE TABLE visitor (  -- 6 rows
  ID NUMBER PRIMARY KEY,
  Name TEXT,  -- values: 'Gonzalo Higuaín ', 'Guti Midfielder', 'Arjen Robben', 'Raúl Brown', 'Fernando Gago', 'Rafael van der Vaart'
  Level_of_membership NUMBER,  -- level of membership | range: 1 to 8
  Age NUMBER  -- range: 25 to 56
);
CREATE TABLE visit (  -- 6 rows
  Museum_ID NUMBER PRIMARY KEY,  -- museum id | FK -> museum.Museum_ID
  visitor_ID TEXT,  -- visitor id | FK -> visitor.ID | TYPE MISMATCH: this col is TEXT, target is NUMBER (no CAST needed in SQLite, but be aware) | values: '5', '3', '6'
  Num_of_Ticket NUMBER,  -- num of ticket | range: 2 to 24
  Total_spent NUMBER  -- total spent | range: 19.98 to 320.44
);