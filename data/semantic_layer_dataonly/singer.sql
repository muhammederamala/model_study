-- db_id: singer
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
CREATE TABLE singer (  -- 8 rows
  Singer_ID NUMBER PRIMARY KEY,  -- singer id
  Name TEXT,  -- values: 'Liliane Bettencourt', 'Christy Walton', 'Alice Walton', 'Iris Fontbona', 'Jacqueline Mars', 'Gina Rinehart', 'Susanne Klatten', 'Abigail Johnson'
  Birth_Year NUMBER,  -- birth year | range: 1940 to 1962
  Net_Worth_Millions NUMBER,  -- net worth millions | range: 12.7 to 30
  Citizenship TEXT  -- values: 'France', 'United States', 'Chile', 'Australia', 'Germany'
);
CREATE TABLE song (  -- 8 rows
  Song_ID NUMBER PRIMARY KEY,  -- song id
  Title TEXT,  -- values: "Do They Know It's Christmas", "F**k It (I Don't Want You Back)", 'Cha Cha Slide', 'Call on Me', 'Yeah', 'All This Time', 'Left Outside Alone', 'Mysterious Girl'
  Singer_ID NUMBER,  -- singer id | FK -> singer.Singer_ID
  Sales NUMBER,  -- range: 261000 to 1094000
  Highest_Position NUMBER  -- highest position | range: 1 to 3
);