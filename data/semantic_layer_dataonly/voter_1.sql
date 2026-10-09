-- db_id: voter_1
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
CREATE TABLE AREA_CODE_STATE (  -- 305 rows
  area_code NUMBER PRIMARY KEY,  -- area code
  state TEXT
);
CREATE TABLE CONTESTANTS (  -- 11 rows
  contestant_number NUMBER PRIMARY KEY,  -- contestant number
  contestant_name TEXT  -- contestant name | values: 'Edwina Burnam', 'Tabatha Gehling', 'Kelly Clauss', 'Jessie Alloway', 'Alana Bregman', 'Jessie Eichman', 'Allie Rogalski', 'Nita Coster', 'Kurt Walser', 'Ericka Dieter', 'Loraine NygrenTania Mattioli'
);
CREATE TABLE VOTES (  -- 4 rows
  vote_id NUMBER PRIMARY KEY,  -- vote id
  phone_number NUMBER,  -- phone number | range: 5112677315 to 7182887233
  state TEXT,  -- FK -> AREA_CODE_STATE.state | JOINS BY NON-PRIMARY-KEY COLUMN (target is not AREA_CODE_STATE's own primary key) | values: 'NY', 'CA', 'NJ\n'
  contestant_number NUMBER,  -- contestant number | FK -> CONTESTANTS.contestant_number | range: 2 to 5
  created TIME
);