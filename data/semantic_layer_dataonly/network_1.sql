-- db_id: network_1
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
CREATE TABLE Highschooler (  -- 16 rows
  ID NUMBER PRIMARY KEY,
  name TEXT,
  grade NUMBER  -- range: 9 to 12
);
CREATE TABLE Friend (  -- 20 rows
  student_id NUMBER PRIMARY KEY,  -- student id | FK -> Highschooler.ID
  friend_id NUMBER  -- friend id | FK -> Highschooler.ID
);
CREATE TABLE Likes (  -- 10 rows
  student_id NUMBER PRIMARY KEY,  -- student id | FK -> Highschooler.ID
  liked_id NUMBER  -- liked id | FK -> Highschooler.ID
);