-- db_id: wta_1
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
CREATE TABLE players (  -- 20662 rows
  player_id NUMBER PRIMARY KEY,  -- player id
  first_name TEXT,  -- first name
  last_name TEXT,  -- last name
  hand TEXT,  -- values: 'R', 'L', 'U'
  birth_date TIME,  -- birth date
  country_code TEXT  -- country code
);
CREATE TABLE matches (  -- 278 rows
  best_of NUMBER,  -- best of
  draw_size NUMBER,  -- draw size | range: 4 to 128
  loser_age NUMBER,  -- loser age | range: 21.0896646133 to 37.138945927399995
  loser_entry TEXT,  -- loser entry
  loser_hand TEXT,  -- loser hand | values: 'R', 'L'
  loser_ht NUMBER,  -- loser ht | range: 157 to 185
  loser_id NUMBER,  -- loser id | FK -> players.player_id
  loser_ioc TEXT,  -- loser ioc
  loser_name TEXT,  -- loser name
  loser_rank NUMBER,  -- loser rank | range: 1 to 112
  loser_rank_points NUMBER,  -- loser rank points | range: 544 to 9945
  loser_seed NUMBER,  -- loser seed | range: 1 to 32
  match_num NUMBER,  -- match num | range: 148 to 300
  minutes NUMBER,  -- range: 0 to 199
  round TEXT,  -- values: 'RR', 'SF', 'QF', 'R32', 'F', 'R16', 'BR'
  score TEXT,
  surface TEXT,  -- values: 'Hard', 'Clay', 'Grass'
  tourney_date TIME,  -- tourney date
  tourney_id TEXT,  -- tourney id
  tourney_level TEXT,  -- tourney level | values: 'W', 'I', 'G', 'P'
  tourney_name TEXT,  -- tourney name
  winner_age NUMBER,  -- winner age | range: 20.917180013699998 to 37.196440794000004
  winner_entry TEXT,  -- winner entry
  winner_hand TEXT,  -- winner hand | values: 'R', 'L'
  winner_ht NUMBER,  -- winner ht | range: 159 to 185
  winner_id NUMBER,  -- winner id | FK -> players.player_id
  winner_ioc TEXT,  -- winner ioc
  winner_name TEXT,  -- winner name
  winner_rank NUMBER,  -- winner rank | range: 1 to 82
  winner_rank_points NUMBER,  -- winner rank points | range: 845 to 12040
  winner_seed NUMBER,  -- winner seed | range: 1 to 30
  year NUMBER  -- range: 2013 to 2017
);
CREATE TABLE rankings (  -- 510437 rows
  ranking_date TIME,  -- ranking date
  ranking NUMBER,  -- range: 1 to 1507
  player_id NUMBER,  -- player id | FK -> players.player_id
  ranking_points NUMBER,  -- ranking points | range: 0 to 13615
  tours NUMBER  -- range: 0 to 41
);