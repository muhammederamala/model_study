# Reviewed structural semantics for Spider dev databases

This is a human-authored review of the 20 schemas and their SQLite rows. It uses schema metadata and database contents, not Spider questions or reference SQL. It records relationships, row-grain risks, and data quirks that a text-to-SQL system should know. Spider supplies no business glossary, so these are **structural observations**, not approved business definitions. The generated JSON in `semantic_catalog/` is a searchable fact index; this file contains the reviewed interpretation.

## battle_death

`battle` records battles; `ship.lost_in_battle` points to a battle, and `death.caused_by_ship_id` points to a ship. A battle can have multiple ships. There is no declared direct battle-to-death join: traverse through `ship`. `death.killed` and `death.injured` are attributes of death records, not of battles or ships.

## car_1

The path is `continents` → `countries` → `car_makers` → `model_list` → `car_names` → `cars_data`, following the declared keys. `car_names.Make` holds full car designations such as `chevrolet chevelle malibu`; `car_names.Model` holds shorter labels such as `chevrolet`. Those names are potentially misleading, so select the value column from observed data rather than from the English word “make” alone. `cars_data` contains measured attributes such as cylinders, horsepower, weight, and acceleration.

## concert_singer

`concert` occurs at a `stadium`; `singer_in_concert` links singers to concerts. The bridge has 10 rows but only 6 distinct `concert_ID` values, despite Spider marking that column as a primary key. Count distinct concerts or singers at the intended grain after joining.

## course_teach

`course_arrange` links `course` and `teacher` and carries `Grade`. Its `Course_ID` repeats in the SQLite rows, so it is an assignment record, not one row per course. `course.Staring_Date` is the physical column spelling; its intended business meaning is unconfirmed.

## cre_Doc_Template_Mgt

The declared chain is template type → template → document → paragraph. A document references a template; paragraphs reference a document. `Version_Number` belongs to a template, while `Paragraph_Text` belongs to a paragraph.

## dog_kennels

`Dogs` links to an owner, breed, and size. `Treatments` links to a dog, professional, and treatment type and records cost and date. A dog can have multiple treatments; aggregating dog age, weight, or count after a treatment join can duplicate dogs. `Charges` has no declared relationship to the other tables, so its `charge_amount` must not be substituted for `Treatments.cost_of_treatment` without an explicit rule.

## employee_hire_evaluation

`hiring` links employees and shops. `evaluation` links to employee and has year and bonus. Its `Employee_ID` repeats in the data: employee `1` has evaluations in 2011 and 2016. Treat evaluations as separate records, not one row per employee, despite the metadata primary-key label.

## flight_2

`flights.SourceAirport` and `flights.DestAirport` are two different roles pointing to `airports.AirportCode`; retain both join alternatives. Every one of the 1,200 observed `flights.Airline` values matches `airlines.uid`, although Spider does not declare that foreign key. Airport codes in `flights` have a leading space: direct equality to `airports.AirportCode` matches **0/1,200**, while equality after `TRIM` matches **1,200/1,200** in this database snapshot. Preserve that distinction when comparing or joining codes.

## museum_visit

`visit` links a visitor and museum and records ticket count and total spent. Its `Museum_ID` repeats, despite the metadata primary-key label. Count museums, visitors, and visit records at separate grains.

## network_1

`Friend` and `Likes` each connect two `Highschooler` rows in distinct roles (`student_id` versus `friend_id` or `liked_id`). A student may have multiple edges. The tables do not establish that an edge is reciprocal; a reverse relationship needs a separate matching row.

## orchestra

An `orchestra` references a conductor; `performance` references an orchestra; `show` references a performance. `show` has no declared primary key. Ratings, weekly rank, and share are performance columns, while result and attendance are show columns.

## pets_1

`Has_Pet` links students and pets. Its `StuID` repeats in the observed rows, so use the bridge when asking which students own which pets and avoid counting one student once per pet unless intended. `Student.Advisor` has no declared relationship in this schema.

## poker_player

`poker_player.People_ID` references `people.People_ID`. The current five poker-player rows have five distinct people IDs. Earnings, money rank, and finishing fields belong to poker-player records; nationality, name, birth date, and height belong to people. The units and ranking conventions are not documented.

## real_estate_properties

`Properties` references a property type. `Other_Property_Features` links properties to available features; those features reference feature types. `Properties` also has separate `apt_feature_*`, `fld_feature_*`, `hse_feature_*`, `oth_feature_*`, and `shp_feature_*` columns. Their codes are not declared as foreign keys to the feature tables, so do not conflate these two representations without further evidence. Requested, offered, and agreed prices are different columns.

## singer

`song.Singer_ID` points to `singer.Singer_ID`. Song sales and highest chart position belong to songs; birth year, net worth, and citizenship belong to singers. The schema does not document sales units or the precise chart behind `Highest_Position`.

## student_transcripts_tracking

Students have **current and permanent** address roles pointing to the same `Addresses` table. Enrolment links a student, degree program, and semester. `Student_Enrolment_Courses` links enrolment to courses; `Transcript_Contents` links transcript records to student-course records. Courses can also have sections. Preserve these grains when counting students, enrolments, courses, and transcripts.

## tvshow

`TV_series.Channel` and `Cartoon.Channel` each point to `TV_Channel.id`; there is no declared direct TV-series-to-cartoon link. Episode, air date, rating, and viewers belong to `TV_series`; title, director, writer, and original air date belong to `Cartoon`. The exact meaning of `TV_Channel.series_name` relative to the other tables is not documented.

## voter_1

`VOTES` records individual votes and points to a contestant. Its `state` joins to `AREA_CODE_STATE.state`, but `state` is not unique there: the 305 area-code rows cover 51 states. A direct join can multiply vote rows; use a distinct state set or existence check when the question is about votes by state.

## world_1

`city.CountryCode` and `countrylanguage.CountryCode` point to `country.Code`. `country.Capital` is **not declared** as a foreign key, but all 232 non-null observed capital IDs match a city ID in the same country. `countrylanguage` has multiple rows per country, despite its metadata primary-key label. `sqlite_sequence` is an internal SQLite table and is excluded from the grounding catalog.

## wta_1

`matches.winner_id` and `matches.loser_id` are distinct roles pointing to `players.player_id`; do not replace one with the other. `rankings` contains records by player and ranking date and has no declared primary key. A player can appear in multiple matches and rankings, so join and aggregate at the question's intended grain.
