-- db_id: dog_kennels
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
CREATE TABLE Breeds (  -- 3 rows
  breed_code TEXT PRIMARY KEY,  -- breed code | values: 'BUL', 'ESK', 'HUS'
  breed_name TEXT  -- breed name | values: 'Eskimo', 'Husky', 'Bulldog'
);
CREATE TABLE Charges (  -- 3 rows
  charge_id NUMBER PRIMARY KEY,  -- charge id
  charge_type TEXT,  -- charge type | values: 'Daily Accommodation', 'Drugs', 'Health Check'
  charge_amount NUMBER  -- charge amount | range: 98 to 640
);
CREATE TABLE Sizes (  -- 3 rows
  size_code TEXT PRIMARY KEY,  -- size code | values: 'LGE', 'MED', 'SML'
  size_description TEXT  -- size description | values: 'Small', 'Medium', 'Large'
);
CREATE TABLE Treatment_Types (  -- 3 rows
  treatment_type_code TEXT PRIMARY KEY,  -- treatment type code | values: 'EXAM', 'VAC', 'WALK'
  treatment_type_description TEXT  -- treatment type description | values: 'Physical examination', 'Vaccination', 'Take for a Walk'
);
CREATE TABLE Owners (  -- 15 rows
  owner_id NUMBER PRIMARY KEY,  -- owner id
  first_name TEXT,  -- first name
  last_name TEXT,  -- last name
  street TEXT,
  city TEXT,
  state TEXT,
  zip_code TEXT,  -- zip code
  email_address TEXT,  -- email address
  home_phone TEXT,  -- home phone
  cell_number TEXT  -- cell number
);
CREATE TABLE Dogs (  -- 15 rows
  dog_id NUMBER PRIMARY KEY,  -- dog id
  owner_id NUMBER,  -- owner id | FK -> Owners.owner_id
  abandoned_yn TEXT,  -- abandoned yn | values: '1', '0'
  breed_code TEXT,  -- breed code | FK -> Breeds.breed_code | values: 'ESK', 'BUL', 'HUS'
  size_code TEXT,  -- size code | FK -> Sizes.size_code | values: 'LGE', 'MED', 'SML'
  name TEXT,
  age TEXT,  -- values: '6', '9', '8', '5', '4', '2', '3', '1'
  date_of_birth TIME,  -- date of birth
  gender TEXT,  -- values: '1', '0'
  weight TEXT,
  date_arrived TIME,  -- date arrived
  date_adopted TIME,  -- date adopted
  date_departed TIME  -- date departed
);
CREATE TABLE Professionals (  -- 15 rows
  professional_id NUMBER PRIMARY KEY,  -- professional id
  role_code TEXT,  -- role code | values: 'Employee', 'Veterenarian'
  first_name TEXT,  -- first name
  street TEXT,
  city TEXT,
  state TEXT,
  zip_code TEXT,  -- zip code
  last_name TEXT,  -- last name
  email_address TEXT,  -- email address
  home_phone TEXT,  -- home phone
  cell_number TEXT  -- cell number
);
CREATE TABLE Treatments (  -- 15 rows
  treatment_id NUMBER PRIMARY KEY,  -- treatment id
  dog_id NUMBER,  -- dog id | FK -> Dogs.dog_id
  professional_id NUMBER,  -- professional id | FK -> Professionals.professional_id
  treatment_type_code TEXT,  -- treatment type code | FK -> Treatment_Types.treatment_type_code | values: 'WALK', 'VAC', 'EXAM'
  date_of_treatment TIME,  -- date of treatment
  cost_of_treatment NUMBER  -- cost of treatment | range: 139 to 945
);