-- db_id: course_teach
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
CREATE TABLE course (  -- 10 rows
  Course_ID NUMBER PRIMARY KEY,  -- course id
  Staring_Date TEXT,  -- staring date | values: '5 May', '6 May', '7 May', '9 May', '10 May', '11 May', '13 May', '14 May', '15 May', '17 May'
  Course TEXT  -- values: 'Language Arts', 'Math', 'Science', 'History', 'Bible', 'Geography', 'Sports', 'French', 'Health', 'Music'
);
CREATE TABLE teacher (  -- 7 rows
  Teacher_ID NUMBER PRIMARY KEY,  -- teacher id
  Name TEXT,  -- values: 'Joseph Huts', 'Gustaaf Deloor', 'Vicente Carretero', 'John Deloor', 'Kearsley Brown', 'Anne Walker', 'Lucy Wong'
  Age TEXT,  -- values: '32', '29', '26', '33', '45', '41', '39'
  Hometown TEXT  -- values: 'Blackrod Urban District', 'Bolton County Borough', 'Farnworth Municipal Borough', 'Horwich Urban District', 'Kearsley Urban District', 'Little Lever Urban District', 'Turton Urban District'
);
CREATE TABLE course_arrange (  -- 6 rows
  Course_ID NUMBER PRIMARY KEY,  -- course id | FK -> course.Course_ID
  Teacher_ID NUMBER,  -- teacher id | FK -> teacher.Teacher_ID
  Grade NUMBER  -- range: 1 to 7
);