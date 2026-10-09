-- db_id: battle_death
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
CREATE TABLE battle (  -- 8 rows
  id NUMBER PRIMARY KEY,
  name TEXT,  -- values: 'Battle of Adrianople', 'Battle of Serres', 'Battle of Rusion', 'Battle of Rodosto', 'Battle of Messinopolis', 'Battle of Boruy', 'Battle of Philippopolis', 'Siege of Constantinople'
  date TEXT,  -- values: '14 April 1205', 'June 1205', '31 January 1206', 'February 1206', '4 September 1207', '31 June 1208', '1235'
  bulgarian_commander TEXT,  -- bulgarian commander | values: 'Kaloyan', 'Unknown', 'Boril', 'Ivan Asen II'
  latin_commander TEXT,  -- latin commander | values: 'Baldwin I', 'Unknown', 'Thierry de Termond', 'Boniface of Montferrat', 'Henry I', 'John of Brienne'
  result TEXT  -- values: 'Bulgarian victory', 'Latin victory', 'Two Year Truce'
);
CREATE TABLE ship (  -- 7 rows
  lost_in_battle NUMBER,  -- lost in battle | FK -> battle.id | range: 4 to 8
  id NUMBER PRIMARY KEY,
  name TEXT,  -- values: 'Lettice', 'Bon Accord', 'Mary', 'HMS Avon', 'Three Brothers', 'Bacchus', 'HMS Atalanta'
  tonnage TEXT,  -- values: 't', '391', '225'
  ship_type TEXT,  -- ship type | values: 'Brig', '18-gun Brig', '8 gun Brig'
  location TEXT,  -- values: 'English Channel', 'SW Approaches', 'Mid-Atlantic'
  disposition_of_ship TEXT  -- disposition of ship | values: 'Captured', 'Wrecked', 'Scuttled', 'Sank'
);
CREATE TABLE death (  -- 13 rows
  caused_by_ship_id NUMBER,  -- caused by ship id | FK -> ship.id
  id NUMBER PRIMARY KEY,
  note TEXT,  -- values: 'Dantewada, Chhattisgarh', 'Erraboru, Chhattisgarh', 'East Champaran, Bihar', 'Gajapati, Odisha', 'Sundargarh, Odisha', 'Kanker, Chhattisgarh', 'WestMidnapore, West Bengal', 'Bastar, Chattisgarh', 'Bokaro, Jharkhand'
  killed NUMBER,  -- range: 0 to 29
  injured NUMBER  -- range: 0 to 9
);