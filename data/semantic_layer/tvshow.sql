-- db_id: tvshow
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
-- Usage patterns mined from real questions follow at the bottom.
CREATE TABLE TV_Channel (  -- 15 rows
  id TEXT PRIMARY KEY,
  series_name TEXT,  -- series name
  Country TEXT,  -- values: 'Italy', 'United Kingdom', 'Poland'
  Language TEXT,  -- values: 'Italian', 'English'
  Content TEXT,  -- values: 'music'
  Pixel_aspect_ratio_PAR TEXT,  -- pixel aspect ratio par | values: '4:3', '4:3 / 16:9', '16:9'
  Hight_definition_TV TEXT,  -- hight definition tv | values: 'no', 'yes'
  Pay_per_view_PPV TEXT,  -- pay per view ppv | values: 'no'
  Package_Option TEXT  -- package option | values: 'Sky Famiglia', 'no ( FTV )', 'Sky Famiglia + Sky HD', 'Option'
);
CREATE TABLE TV_series (  -- 12 rows
  id NUMBER PRIMARY KEY,
  Episode TEXT,  -- values: 'A Love of a Lifetime', 'Friendly Skies', 'Game Three', 'The Year of the Rabbit', 'The Legend of Dylan McCleen', 'Keepers', 'Double Down', 'Winterland', 'Emily', 'Blowback', 'Home By Another Way', 'The Hanged Man'
  Air_Date TEXT,  -- air date | values: 'September 24, 2007', 'October 1, 2007', 'October 8, 2007', 'October 15, 2007', 'October 22, 2007', 'October 29, 2007', 'November 5, 2007', 'November 12, 2007', 'November 19, 2007', 'November 26, 2007', 'December 10, 2007', 'December 17, 2007'
  Rating TEXT,  -- values: '5.8', '5.3', '4.4', '4.3', '3.8', '3.7', '3.4', '4.0', '3.5', '3.0'
  Share NUMBER,  -- range: 5 to 9
  18_49_Rating_Share TEXT,  -- 18 49 rating share | values: '3.5/9', '3.2/8', '2.9/7', '2.7/7', '2.4/6', '2.2/6', '2.1/5', '1.7/5', '1.5/4'
  Viewers_m TEXT,  -- viewers m | values: '9.16', '8.23', '6.94', '6.75', '6.06', '5.75', '5.13', '6.09', '5.61', '6.05', '5.28', '4.24'
  Weekly_Rank NUMBER,  -- weekly rank | range: 43 to 80
  Channel TEXT  -- FK -> TV_Channel.id | values: '700', '701', '707', '713', '714', '708', '717', '719', '728'
);
CREATE TABLE Cartoon (  -- 12 rows
  id NUMBER PRIMARY KEY,
  Title TEXT,  -- values: 'The Rise of the Blue Beetle!', 'Terror on Dinosaur Island!', 'Evil Under the Sea!', 'Day of the Dark Knight!', 'Invasion of the Secret Santas!', 'Enter the Outsiders!', 'Dawn of the Dead Man!', 'Fall of the Blue Beetle!', 'Journey to the Center of the Bat!', 'The Eyes of Despero!', 'Return of the Fearsome Fangs!', 'Deep Cover for Batman!'
  Directed_by TEXT,  -- directed by | values: 'Ben Jones', 'Brandon Vietti', 'Michael Chang'
  Written_by TEXT,  -- written by | values: 'Michael Jelenic', 'Steven Melching', 'Joseph Kuhr', 'J. M. DeMatteis', 'Adam Beechen', 'Todd Casey', 'James Krieg', 'Matt Wayne'
  Original_air_date TEXT,  -- original air date | values: 'November14,2008', 'November21,2008', 'December5,2008', 'January2,2009', 'December12,2008', 'January9,2009', 'January16,2009', 'January23,2009', 'January30,2009', 'February6,2009', 'February20,2009', 'February27,2009'
  Production_code NUMBER,  -- production code | range: 101 to 112
  Channel TEXT  -- FK -> TV_Channel.id | values: '700', '701', '703', '704', '705', '706', '707', '708', '728'
);

-- ============================================================
-- USAGE PATTERNS for tvshow
-- Mined from 62 real analyst questions against this database.
-- Heuristic (regex-derived, not a SQL parser) — treat as guidance, not rules.
-- ============================================================
-- Most common join paths (14 of 62 questions join at least two tables):
--    10 questions:  cartoon.channel = tv_channel.id
--     4 questions:  tv_channel.id = tv_series.channel
-- Metrics this database is usually asked for:
--    18 questions:  COUNT(*)  (plain row counts are the single most common ask)
--     2 questions:  COUNT(series_name)
--     2 questions:  COUNT(content)
--     2 questions:  MAX(share)
--     2 questions:  MIN(share)
-- Phrasing -> SQL constructs seen in this database's questions:
--   'how many' / 'number of' -> COUNT
--   'for each' / 'per <thing>' / 'by <thing>' -> GROUP BY
--   'most' / 'highest' / 'largest' / 'top' -> ORDER BY ... DESC
--   'the single most/least ...' -> ORDER BY ... LIMIT 1
--   'never' / 'without any' / 'that do not' -> NOT IN / EXCEPT
--   'both X and Y' -> INTERSECT
--   'more than the average' / comparisons to an aggregate -> subquery