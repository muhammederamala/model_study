-- db_id: student_transcripts_tracking
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
-- Usage patterns mined from real questions follow at the bottom.
CREATE TABLE Addresses (  -- 15 rows
  address_id NUMBER PRIMARY KEY,  -- address id
  line_1 TEXT,  -- line 1
  line_2 TEXT,  -- line 2
  line_3 TEXT,  -- line 3
  city TEXT,
  zip_postcode TEXT,  -- zip postcode
  state_province_county TEXT,  -- state province county
  country TEXT,
  other_address_details TEXT  -- other address details
);
CREATE TABLE Courses (  -- 15 rows
  course_id NUMBER PRIMARY KEY,  -- course id
  course_name TEXT,  -- course name
  course_description TEXT,  -- course description | values: 'p', 'q', 'v', 'k', 'c', 'n', 'l', 'b', 'w', 'd'
  other_details TEXT  -- other details
);
CREATE TABLE Departments (  -- 15 rows
  department_id NUMBER PRIMARY KEY,  -- department id
  department_name TEXT,  -- department name
  department_description TEXT,  -- department description
  other_details TEXT  -- other details
);
CREATE TABLE Degree_Programs (  -- 15 rows
  degree_program_id NUMBER PRIMARY KEY,  -- degree program id
  department_id NUMBER,  -- department id | FK -> Departments.department_id
  degree_summary_name TEXT,  -- degree summary name | values: 'Master', 'Bachelor', 'PHD'
  degree_summary_description TEXT,  -- degree summary description
  other_details TEXT  -- other details
);
CREATE TABLE Sections (  -- 15 rows
  section_id NUMBER PRIMARY KEY,  -- section id
  course_id NUMBER,  -- course id | FK -> Courses.course_id
  section_name TEXT,  -- section name
  section_description TEXT,  -- section description
  other_details TEXT  -- other details
);
CREATE TABLE Semesters (  -- 15 rows
  semester_id NUMBER PRIMARY KEY,  -- semester id
  semester_name TEXT,  -- semester name
  semester_description TEXT,  -- semester description | values: 'x', 'g', 'w', 'c', 'l', 'y', 'f', 'm', 'q', 't', 'o'
  other_details TEXT  -- other details
);
CREATE TABLE Students (  -- 15 rows
  student_id NUMBER PRIMARY KEY,  -- student id
  current_address_id NUMBER,  -- current address id | FK -> Addresses.address_id
  permanent_address_id NUMBER,  -- permanent address id | FK -> Addresses.address_id
  first_name TEXT,  -- first name
  middle_name TEXT,  -- middle name
  last_name TEXT,  -- last name
  cell_mobile_number TEXT,  -- cell mobile number
  email_address TEXT,  -- email address
  ssn TEXT,
  date_first_registered TIME,  -- date first registered
  date_left TIME,  -- date left
  other_student_details TEXT  -- other student details
);
CREATE TABLE Student_Enrolment (  -- 15 rows
  student_enrolment_id NUMBER PRIMARY KEY,  -- student enrolment id
  degree_program_id NUMBER,  -- degree program id | FK -> Degree_Programs.degree_program_id
  semester_id NUMBER,  -- semester id | FK -> Semesters.semester_id
  student_id NUMBER,  -- student id | FK -> Students.student_id
  other_details TEXT  -- other details
);
CREATE TABLE Student_Enrolment_Courses (  -- 15 rows
  student_course_id NUMBER PRIMARY KEY,  -- student course id
  course_id NUMBER,  -- course id | FK -> Courses.course_id
  student_enrolment_id NUMBER  -- student enrolment id | FK -> Student_Enrolment.student_enrolment_id
);
CREATE TABLE Transcripts (  -- 15 rows
  transcript_id NUMBER PRIMARY KEY,  -- transcript id
  transcript_date TIME,  -- transcript date
  other_details TEXT  -- other details
);
CREATE TABLE Transcript_Contents (  -- 15 rows
  student_course_id NUMBER,  -- student course id | FK -> Student_Enrolment_Courses.student_course_id
  transcript_id NUMBER  -- transcript id | FK -> Transcripts.transcript_id
);

-- ============================================================
-- USAGE PATTERNS for student_transcripts_tracking
-- Mined from 78 real analyst questions against this database.
-- Heuristic (regex-derived, not a SQL parser) — treat as guidance, not rules.
-- ============================================================
-- Most common join paths (34 of 78 questions join at least two tables):
--     8 questions:  student_enrolment.student_id = students.student_id
--     8 questions:  degree_programs.degree_program_id = student_enrolment.degree_program_id
--     4 questions:  degree_programs.department_id = departments.department_id
--     4 questions:  courses.course_id = student_enrolment_courses.course_id
--     4 questions:  addresses.address_id = students.current_address_id
--     4 questions:  transcript_contents.transcript_id = transcripts.transcript_id
-- Metrics this database is usually asked for:
--    34 questions:  COUNT(*)  (plain row counts are the single most common ask)
--     2 questions:  COUNT(department_id)
--     2 questions:  COUNT(degree_summary_name)
--     2 questions:  AVG(transcript_date)
--     2 questions:  COUNT(current_address_id)
-- Phrasing -> SQL constructs seen in this database's questions:
--   'how many' / 'number of' -> COUNT
--   'average' / 'mean' -> AVG
--   'for each' / 'per <thing>' / 'by <thing>' -> GROUP BY
--   'most' / 'highest' / 'largest' / 'top' -> ORDER BY ... DESC
--   'the single most/least ...' -> ORDER BY ... LIMIT 1
--   'never' / 'without any' / 'that do not' -> NOT IN / EXCEPT
--   'both X and Y' -> INTERSECT
--   'more than the average' / comparisons to an aggregate -> subquery