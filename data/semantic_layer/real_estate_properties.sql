-- db_id: real_estate_properties
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
-- Usage patterns mined from real questions follow at the bottom.
CREATE TABLE Ref_Feature_Types (  -- 2 rows
  feature_type_code TEXT PRIMARY KEY,  -- feature type code | values: 'Amenity', 'Security'
  feature_type_name TEXT  -- feature type name | values: 'Amenity, eg Pool.', 'Securiyt, eg Burglar Alarm.'
);
CREATE TABLE Ref_Property_Types (  -- 5 rows
  property_type_code TEXT PRIMARY KEY,  -- property type code | values: 'Apartment', 'Field', 'House', 'Other', 'Shop'
  property_type_description TEXT  -- property type description | values: 'House, Bungalow, etc.', 'Apartment, Flat, Condo, etc.', 'Field, Meadow.', 'Other, to be determined.', 'Shop, Retail Outlet.'
);
CREATE TABLE Other_Available_Features (  -- 3 rows
  feature_id NUMBER PRIMARY KEY,  -- feature id
  feature_type_code TEXT,  -- feature type code | FK -> Ref_Feature_Types.feature_type_code | values: 'Amenity', 'Security'
  feature_name TEXT,  -- feature name | values: 'AirCon', 'Pool', 'BurglarAlarm'
  feature_description TEXT  -- feature description | values: 'Air Conditioning.', 'Swimming Pool.', 'Burglar Alarm'
);
CREATE TABLE Properties (  -- 15 rows
  property_id NUMBER PRIMARY KEY,  -- property id
  property_type_code TEXT,  -- property type code | FK -> Ref_Property_Types.property_type_code | values: 'House', 'Other', 'Field', 'Apartment', 'Shop'
  date_on_market TIME,  -- date on market
  date_sold TIME,  -- date sold
  property_name TEXT,  -- property name
  property_address TEXT,  -- property address
  room_count NUMBER,  -- room count | range: 1 to 9
  vendor_requested_price NUMBER,  -- vendor requested price | range: 13.4715 to 661536468.4429
  buyer_offered_price NUMBER,  -- buyer offered price | range: 0 to 27537286
  agreed_selling_price NUMBER,  -- agreed selling price | range: 0 to 456840888.16
  apt_feature_1 TEXT,  -- apt feature 1 | values: 'aut', 'est', 'ut', 'nesciunt', 'quo', 'sed', 'quos', 'fuga', 'enim', 'consequatur', 'et', 'qui'
  apt_feature_2 TEXT,  -- apt feature 2
  apt_feature_3 TEXT,  -- apt feature 3
  fld_feature_1 TEXT,  -- fld feature 1
  fld_feature_2 TEXT,  -- fld feature 2
  fld_feature_3 TEXT,  -- fld feature 3
  hse_feature_1 TEXT,  -- hse feature 1
  hse_feature_2 TEXT,  -- hse feature 2
  hse_feature_3 TEXT,  -- hse feature 3
  oth_feature_1 TEXT,  -- oth feature 1
  oth_feature_2 TEXT,  -- oth feature 2
  oth_feature_3 TEXT,  -- oth feature 3
  shp_feature_1 TEXT,  -- shp feature 1
  shp_feature_2 TEXT,  -- shp feature 2
  shp_feature_3 TEXT,  -- shp feature 3
  other_property_details TEXT  -- other property details
);
CREATE TABLE Other_Property_Features (  -- 15 rows
  property_id NUMBER,  -- property id | FK -> Properties.property_id
  feature_id NUMBER,  -- feature id | FK -> Other_Available_Features.feature_id
  property_feature_description TEXT  -- property feature description
);

-- ============================================================
-- USAGE PATTERNS for real_estate_properties
-- Mined from 4 real analyst questions against this database.
-- Heuristic (regex-derived, not a SQL parser) — treat as guidance, not rules.
-- ============================================================
-- Most common join paths (2 of 4 questions join at least two tables):
--     1 questions:  other_available_features.feature_type_code = ref_feature_types.feature_type_code
--     1 questions:  properties.property_type_code = ref_property_types.property_type_code
-- Metrics this database is usually asked for:
--     1 questions:  COUNT(*)  (plain row counts are the single most common ask)