-- db_id: poker_player
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
CREATE TABLE poker_player (  -- 5 rows
  Poker_Player_ID NUMBER PRIMARY KEY,  -- poker player id
  People_ID NUMBER,  -- people id | FK -> people.People_ID
  Final_Table_Made NUMBER,  -- final table made | range: 10 to 42
  Best_Finish NUMBER,  -- best finish | range: 1 to 3
  Money_Rank NUMBER,  -- money rank | range: 58 to 166
  Earnings NUMBER  -- range: 104871 to 596462
);
CREATE TABLE people (  -- 7 rows
  People_ID NUMBER PRIMARY KEY,  -- people id
  Nationality TEXT,  -- values: 'Russia', 'Bulgaria'
  Name TEXT,  -- values: 'Aleksey Ostapenko', 'Teodor Salparov', 'Roman Bragin', 'Sergey Grankin', 'Yevgeni Sivozhelez', 'Maksim Botin', 'Semen Poltavskiy'
  Birth_Date TEXT,  -- birth date | values: 'May 26, 1986', 'August 16, 1982', 'April 17, 1987', 'January 22, 1987', 'August 8, 1986', 'July 14, 1983', 'February 8, 1981'
  Height NUMBER  -- range: 182 to 207
);