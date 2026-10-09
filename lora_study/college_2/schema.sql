-- db_id: college_2
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
CREATE TABLE classroom (  -- 30 rows
  building TEXT,
  room_number TEXT,  -- room number
  capacity NUMBER  -- range: 10 to 120
);
CREATE TABLE department (  -- 20 rows
  dept_name TEXT PRIMARY KEY,  -- dept name
  building TEXT,
  budget NUMBER  -- range: 106378.69 to 942162.76
);
CREATE TABLE course (  -- 200 rows
  course_id TEXT PRIMARY KEY,  -- course id
  title TEXT,
  dept_name TEXT,  -- dept name | FK -> department.dept_name
  credits NUMBER  -- range: 3 to 4
);
CREATE TABLE instructor (  -- 50 rows
  ID TEXT PRIMARY KEY,
  name TEXT,
  dept_name TEXT,  -- dept name | FK -> department.dept_name
  salary NUMBER  -- range: 32241.56 to 124651.41
);
CREATE TABLE section (  -- 100 rows
  course_id TEXT,  -- course id | FK -> course.course_id
  sec_id TEXT,  -- sec id | values: '1', '2', '3'
  semester TEXT,  -- values: 'Fall', 'Spring'
  year NUMBER,  -- range: 2001 to 2010
  building TEXT,  -- FK -> classroom.building
  room_number TEXT,  -- room number | FK -> classroom.room_number | JOINS BY NON-PRIMARY-KEY COLUMN (target is not classroom's own primary key)
  time_slot_id TEXT  -- time slot id
);
CREATE TABLE teaches (  -- 100 rows
  ID TEXT,  -- FK -> instructor.ID
  course_id TEXT,  -- course id | FK -> section.course_id
  sec_id TEXT,  -- sec id | FK -> section.sec_id | JOINS BY NON-PRIMARY-KEY COLUMN (target is not section's own primary key) | values: '1', '2', '3'
  semester TEXT,  -- FK -> section.semester | JOINS BY NON-PRIMARY-KEY COLUMN (target is not section's own primary key) | values: 'Spring', 'Fall'
  year NUMBER  -- FK -> section.year | JOINS BY NON-PRIMARY-KEY COLUMN (target is not section's own primary key) | range: 2001 to 2010
);
CREATE TABLE student (  -- 2000 rows
  ID TEXT PRIMARY KEY,
  name TEXT,
  dept_name TEXT,  -- dept name | FK -> department.dept_name
  tot_cred NUMBER  -- tot cred | range: 0 to 129
);
CREATE TABLE takes (  -- 30000 rows
  ID TEXT,  -- FK -> student.ID
  course_id TEXT,  -- course id | FK -> section.course_id
  sec_id TEXT,  -- sec id | FK -> section.sec_id | JOINS BY NON-PRIMARY-KEY COLUMN (target is not section's own primary key) | values: '1', '2', '3'
  semester TEXT,  -- FK -> section.semester | JOINS BY NON-PRIMARY-KEY COLUMN (target is not section's own primary key) | values: 'Fall', 'Spring'
  year NUMBER,  -- FK -> section.year | JOINS BY NON-PRIMARY-KEY COLUMN (target is not section's own primary key) | range: 2001 to 2010
  grade TEXT  -- values: 'C-', 'B-', 'A-', 'A ', 'B+', 'B ', 'C+', 'A+', 'C '
);
CREATE TABLE advisor (  -- 2000 rows
  s_ID TEXT PRIMARY KEY,  -- s id | FK -> student.ID
  i_ID TEXT  -- i id | FK -> instructor.ID
);
CREATE TABLE time_slot (  -- 20 rows
  time_slot_id TEXT,  -- time slot id | values: 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'
  day TEXT,  -- values: 'F', 'M', 'W', 'R', 'T'
  start_hr NUMBER,  -- start hr | range: 8 to 16
  start_min NUMBER,  -- start min | range: 0 to 30
  end_hr NUMBER,  -- end hr | range: 8 to 16
  end_min NUMBER  -- end min | range: 30 to 50
);
CREATE TABLE prereq (  -- 100 rows
  course_id TEXT,  -- course id | FK -> course.course_id
  prereq_id TEXT  -- prereq id | FK -> course.course_id
);
