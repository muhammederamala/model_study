-- db_id: orchestra
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
CREATE TABLE conductor (  -- 12 rows
  Conductor_ID NUMBER PRIMARY KEY,  -- conductor id
  Name TEXT,  -- values: 'Antal Doráti', 'Igor Stravinsky', 'Colin Davis', 'Paul Jorgensen', 'Antal Brown', 'Charles Dutoit', 'Gerard Schwarz', 'Pierre Boulez', 'Valeri Gergiev', 'Robert Craft', 'Seiji Ozawa', 'Michael Tilson Thomas'
  Age NUMBER,  -- range: 40 to 63
  Nationality TEXT,  -- values: 'USA', 'UK', 'France'
  Year_of_Work NUMBER  -- year of work | range: 6 to 21
);
CREATE TABLE orchestra (  -- 12 rows
  Orchestra_ID NUMBER PRIMARY KEY,  -- orchestra id
  Orchestra TEXT,  -- values: 'London Symphony Orchestra', 'Columbia Symphony Orchestra', 'Royal Concertgebouw Orchestra', 'Royal Danish Orchestra', 'Detroit Symphony Orchestra', 'Montreal Symphony Orchestra', 'Seattle Symphony Orchestra', 'Chicago Symphony Orchestra', 'Kirov Orchestra', 'Philharmonia Orchestra', 'Orchestre de Paris', 'San Francisco Symphony Orchestra'
  Conductor_ID NUMBER,  -- conductor id | FK -> conductor.Conductor_ID
  Record_Company TEXT,  -- record company | values: 'Mercury Records', 'Columbia Masterworks', 'Philips', 'Kultur', 'Decca Records', 'Delos Records', 'Deutsche Grammophon', 'Philips Classics Records', 'Koch Records / Naxos Records', 'EMI', 'RCA'
  Year_of_Founded NUMBER,  -- year of founded | range: 2002 to 2009
  Major_Record_Format TEXT  -- major record format | values: 'CD', 'CD / LP', 'DVD'
);
CREATE TABLE performance (  -- 11 rows
  Performance_ID NUMBER PRIMARY KEY,  -- performance id
  Orchestra_ID NUMBER,  -- orchestra id | FK -> orchestra.Orchestra_ID
  Type TEXT,  -- values: 'Auditions 1', 'Auditions 2', 'Auditions 3', 'Auditions 4', 'Auditions 5', 'Semi-final 1', 'Semi-final 2', 'Semi-final 3', 'Live final', 'Live final results', 'Series average'
  Date TEXT,  -- values: '9 June', '10 June', '11 June', '12 June', '13 June', '14 June', '15 June', '16 June', '17 June', '2007'
  Official_ratings_(millions) NUMBER,  -- official ratings (millions) | range: 5.2 to 11.58
  Weekly_rank TEXT,  -- weekly rank | values: '12', '8', '15', '13', '11', '9', '7', '1', '2', 'TBC'
  Share TEXT  -- values: '22.7%', '28.0%', '29.4%', '29.3%', '29.2%', '34.0%', '38.1%', '40.9%', '43.7%', '44.7%', '34%'
);
CREATE TABLE show (  -- 5 rows
  Show_ID NUMBER,  -- show id
  Performance_ID NUMBER,  -- performance id | FK -> performance.Performance_ID
  If_first_show OTHERS,  -- if first show
  Result TEXT,  -- values: 'T', 'F'
  Attendance NUMBER  -- range: 555 to 2431
);