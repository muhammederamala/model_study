-- db_id: cre_Doc_Template_Mgt
-- Schema annotated with readable column names, real sample values and
-- value ranges taken from the data, and auto-detected join quirks.
CREATE TABLE Ref_Template_Types (  -- 5 rows
  Template_Type_Code TEXT PRIMARY KEY,  -- template type code | values: 'AD', 'BK', 'CV', 'PP', 'PPT'
  Template_Type_Description TEXT  -- template type description | values: 'Presentation', 'CV', 'Advertisement', 'Paper', 'Book'
);
CREATE TABLE Templates (  -- 20 rows
  Template_ID NUMBER PRIMARY KEY,  -- template id
  Version_Number NUMBER,  -- version number | range: 0 to 9
  Template_Type_Code TEXT,  -- template type code | FK -> Ref_Template_Types.Template_Type_Code | values: 'PP', 'BK', 'PPT', 'AD', 'CV'
  Date_Effective_From TIME,  -- date effective from
  Date_Effective_To TIME,  -- date effective to
  Template_Details TEXT  -- template details
);
CREATE TABLE Documents (  -- 15 rows
  Document_ID NUMBER PRIMARY KEY,  -- document id
  Template_ID NUMBER,  -- template id | FK -> Templates.Template_ID
  Document_Name TEXT,  -- document name
  Document_Description TEXT,  -- document description | values: 'n', 'y', 'u', 'h', 'w', 'k', 'z', 'r', 'f', 'b'
  Other_Details TEXT  -- other details
);
CREATE TABLE Paragraphs (  -- 15 rows
  Paragraph_ID NUMBER PRIMARY KEY,  -- paragraph id
  Document_ID NUMBER,  -- document id | FK -> Documents.Document_ID
  Paragraph_Text TEXT,  -- paragraph text
  Other_Details TEXT  -- other details
);