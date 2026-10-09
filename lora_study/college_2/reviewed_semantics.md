# Reviewed structural notes

These notes come from Spider schema metadata and the populated SQLite database, not from question/SQL pairs. They describe structure, not approved business metrics.

## college_2

`department` links to courses, instructors, and students through `dept_name`. `classroom` identifies a room by its building and room number; joining `section` to `classroom` requires both columns. `section` is identified by course, section ID, semester, and year. Both `takes` and `teaches` refer to a section through that full set of columns; joining on course ID alone can multiply rows or mix terms. `takes.ID` identifies a student, while `teaches.ID` identifies an instructor. `advisor.s_ID` and `advisor.i_ID` refer to student and instructor roles. `prereq.course_id` is the course that has a prerequisite; `prereq.prereq_id` is the required course. `time_slot` has multiple rows per `time_slot_id` for different days. `section.time_slot_id` has no declared foreign key; in this SQLite snapshot only 51 of 100 sections have a code found in `time_slot`, and joining those sections produces 131 rows because of multiple days. Spider labels `classroom.building`, `section.course_id`, `teaches.ID`, `takes.ID`, `time_slot.time_slot_id`, and `prereq.course_id` as primary keys, but each repeats in the SQLite rows; the prompt schema and catalog omit those false single-column key claims.
