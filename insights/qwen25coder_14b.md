# Qwen 2.5 Coder 14B: Spider dev failure analysis

Source: `results/runs/spider_baseline/results_qwen25coder_14b.csv` and the same-question Llama CSV. All 1,032 IDs are present and unique.
The prompt uses the database-derived `semantic_layer_dataonly` schema.
Accuracy means matching gold SQL results on one SQLite database; it does not prove semantic equivalence on every possible database.

## Outcome

| Model | Correct / 1,032 | Accuracy |
|---|---:|---:|
| Qwen 2.5 Coder 14B | 808/1032 | 78.3% |
| Llama 3.1 8B | 733/1032 | 71.0% |

Qwen has 224 mismatches: 11 SQL execution errors and 213 executable queries with different results.

| Paired outcome | Questions |
|---|---:|
| Qwen right, Llama wrong | 125 |
| Llama right, Qwen wrong | 50 |
| Both wrong | 174 |
| Both right | 683 |

## Accuracy by local complexity bucket

These are this project's heuristic buckets, not Spider's official hardness labels.

| Bucket | Qwen | Llama | Qwen SQL errors |
|---|---:|---:|---:|
| simple | 451/497 (90.7%) | 434/497 (87.3%) | 4 |
| moderate | 246/364 (67.6%) | 205/364 (56.3%) | 6 |
| complex | 111/171 (64.9%) | 94/171 (55.0%) | 1 |

## SQL constructs in gold queries

Construct groups overlap; this is a diagnostic split, not a causal attribution.

| Construct | N | Qwen correct | Llama correct |
|---|---:|---:|---:|
| JOIN | 408 | 290 (71.1%) | 238 (58.3%) |
| GROUP BY | 277 | 179 (64.6%) | 162 (58.5%) |
| HAVING | 79 | 57 (72.2%) | 45 (57.0%) |
| nested SELECT | 159 | 106 (66.7%) | 77 (48.4%) |
| set operation | 80 | 55 (68.8%) | 41 (51.2%) |
| DISTINCT | 87 | 62 (71.3%) | 49 (56.3%) |
| AVG or SUM | 94 | 54 (57.4%) | 53 (56.4%) |

## Execution errors

| SQLite error prefix | Count |
|---|---:|
| no such column | 8 |
| ambiguous column name | 3 |

## Databases with the most mismatches

| Database | Qwen correct / N | Llama correct / N |
|---|---:|---:|
| world_1 | 69/120 | 58/120 |
| car_1 | 59/92 | 42/92 |
| student_transcripts_tracking | 50/78 | 49/78 |
| wta_1 | 39/60 | 35/60 |
| dog_kennels | 64/82 | 53/82 |
| cre_Doc_Template_Mgt | 74/84 | 73/84 |
| network_1 | 46/56 | 44/56 |
| pets_1 | 32/42 | 28/42 |
| flight_2 | 72/80 | 70/80 |
| tvshow | 55/62 | 55/62 |

## Invalid SQL examples

- **ID 150 · car_1 · simple**: What are the makers and models?
  - Gold: `SELECT Maker , Model FROM MODEL_LIST;`
  - Qwen: `SELECT Maker, Model FROM car_makers JOIN model_list ON car_makers.Id = model_list.Maker;`
  - SQLite error: `ambiguous column name: Maker`
- **ID 369 · car_1 · moderate**: For a volvo model, how many cylinders does the version with least accelerate have?
  - Gold: `SELECT T1.cylinders FROM CARS_DATA AS T1 JOIN CAR_NAMES AS T2 ON T1.Id = T2.MakeId WHERE T2.Model = 'volvo' ORDER BY T1.accelerate ASC LIMIT 1;`
  - Qwen: `SELECT Cylinders FROM cars_data WHERE Id = ( SELECT MakeId FROM car_names WHERE Make = 'volvo' ORDER BY Accelerate ASC LIMIT 1 );`
  - SQLite error: `no such column: Accelerate`
- **ID 455 · car_1 · moderate**: For model volvo, how many cylinders does the car with the least accelerate have?
  - Gold: `SELECT T1.cylinders FROM CARS_DATA AS T1 JOIN CAR_NAMES AS T2 ON T1.Id = T2.MakeId WHERE T2.Model = 'volvo' ORDER BY T1.accelerate ASC LIMIT 1;`
  - Qwen: `SELECT Cylinders FROM cars_data WHERE Id = ( SELECT MakeId FROM car_names WHERE Model = 'volvo' ORDER BY Accelerate ASC LIMIT 1 );`
  - SQLite error: `no such column: Accelerate`
- **ID 601 · car_1 · simple**: What are all the makers and models?
  - Gold: `SELECT Maker , Model FROM MODEL_LIST;`
  - Qwen: `SELECT Maker, Model FROM car_makers JOIN model_list ON car_makers.Id = model_list.Maker;`
  - SQLite error: `ambiguous column name: Maker`
- **ID 606 · car_1 · moderate**: Among the cars that do not have the minimum horsepower , what are the make ids and names of all those with less than 4 cylinders ?
  - Gold: `select t2.makeid , t2.make from cars_data as t1 join car_names as t2 on t1.id = t2.makeid where t1.horsepower > (select min(horsepower) from cars_data) and t1.cylinders < 4;`
  - Qwen: `SELECT MakeId, Make FROM car_names WHERE MakeId NOT IN ( SELECT MakeId FROM cars_data ORDER BY Horsepower ASC LIMIT 1 ) AND Cylinders < 4;`
  - SQLite error: `no such column: Cylinders`

## Executable mismatches with nested SELECT

- **ID 153 · battle_death · complex**: List the name and date the battle that has lost the ship named 'Lettice' and the ship named 'HMS Atalanta'
  - Gold: `SELECT T1.name , T1.date FROM battle AS T1 JOIN ship AS T2 ON T1.id = T2.lost_in_battle WHERE T2.name = 'Lettice' INTERSECT SELECT T1.name , T1.date FROM battle AS T1 JOIN ship AS T2 ON T1.id = T2.lost_in_battle WHERE T2.name = 'HMS Atalanta'`
  - Qwen: `SELECT b.name, b.date FROM battle b JOIN ship s ON b.id = s.lost_in_battle WHERE s.name IN ('Lettice', 'HMS Atalanta');`
- **ID 238 · car_1 · moderate**: How many cars have a larger accelerate than the car with the largest horsepower?
  - Gold: `SELECT COUNT(*) FROM CARS_DATA WHERE Accelerate > ( SELECT Accelerate FROM CARS_DATA ORDER BY Horsepower DESC LIMIT 1 );`
  - Qwen: `SELECT COUNT(*) FROM cars_data WHERE Accelerate > (SELECT MAX(Horsepower) FROM cars_data);`
- **ID 277 · car_1 · moderate**: What is the number of cars with a greater accelerate than the one with the most horsepower?
  - Gold: `SELECT COUNT(*) FROM CARS_DATA WHERE Accelerate > ( SELECT Accelerate FROM CARS_DATA ORDER BY Horsepower DESC LIMIT 1 );`
  - Qwen: `SELECT COUNT(*) FROM cars_data WHERE Accelerate > (SELECT MAX(Horsepower) FROM cars_data)`
- **ID 308 · car_1 · complex**: Which are the car makers which produce at least 2 models and more than 3 car makers ? List the id and the maker .
  - Gold: `select t1.id , t1.maker from car_makers as t1 join model_list as t2 on t1.id = t2.maker group by t1.id having count(*) >= 2 intersect select t1.id , t1.maker from car_makers as t1 join model_list as t2 on t1.id = t2.maker join car_names as t3 on t2.model = t3.model group by t1.id having count(*) > 3;`
  - Qwen: `SELECT cm.Id, cm.Maker FROM car_makers cm JOIN model_list ml ON cm.Id = ml.Maker GROUP BY cm.Id, cm.Maker HAVING COUNT(ml.ModelId) >= 2 AND COUNT(DISTINCT cm.Id) > 3;`
- **ID 414 · car_1 · complex**: What are the ids and makers of all car makers that produce at least 2 models and make more than 3 cars?
  - Gold: `SELECT T1.Id , T1.Maker FROM CAR_MAKERS AS T1 JOIN MODEL_LIST AS T2 ON T1.Id = T2.Maker GROUP BY T1.Id HAVING count(*) >= 2 INTERSECT SELECT T1.Id , T1.Maker FROM CAR_MAKERS AS T1 JOIN MODEL_LIST AS T2 ON T1.Id = T2.Maker JOIN CAR_NAMES AS T3 ON T2.model = T3.model GROUP BY T1.Id HAVING count(*) > 3;`
  - Qwen: `SELECT cm.Id, cm.Maker FROM car_makers cm JOIN model_list ml ON cm.Id = ml.Maker JOIN car_names cn ON ml.Model = cn.Model GROUP BY cm.Id, cm.Maker HAVING COUNT(DISTINCT ml.Model) >= 2 AND COUNT(cn.MakeId) > 3;`

## Executable mismatches with JOIN

- **ID 153 · battle_death · complex**: List the name and date the battle that has lost the ship named 'Lettice' and the ship named 'HMS Atalanta'
  - Gold: `SELECT T1.name , T1.date FROM battle AS T1 JOIN ship AS T2 ON T1.id = T2.lost_in_battle WHERE T2.name = 'Lettice' INTERSECT SELECT T1.name , T1.date FROM battle AS T1 JOIN ship AS T2 ON T1.id = T2.lost_in_battle WHERE T2.name = 'HMS Atalanta'`
  - Qwen: `SELECT b.name, b.date FROM battle b JOIN ship s ON b.id = s.lost_in_battle WHERE s.name IN ('Lettice', 'HMS Atalanta');`
- **ID 950 · battle_death · complex**: What are the ids and names of the battles that led to more than 10 people killed in total.
  - Gold: `SELECT T1.id , T1.name FROM battle AS T1 JOIN ship AS T2 ON T1.id = T2.lost_in_battle JOIN death AS T3 ON T2.id = T3.caused_by_ship_id GROUP BY T1.id HAVING sum(T3.killed) > 10`
  - Qwen: `SELECT battle.id, battle.name FROM battle JOIN death ON battle.id = death.caused_by_ship_id GROUP BY battle.id, battle.name HAVING SUM(death.killed) > 10;`
- **ID 997 · battle_death · complex**: What is the ship id and name that caused most total injuries?
  - Gold: `SELECT T2.id , T2.name FROM death AS T1 JOIN ship AS t2 ON T1.caused_by_ship_id = T2.id GROUP BY T2.id ORDER BY count(*) DESC LIMIT 1`
  - Qwen: `SELECT T1.id, T1.name FROM ship AS T1 JOIN death AS T2 ON T1.id = T2.caused_by_ship_id GROUP BY T1.id ORDER BY SUM(T2.injured) DESC LIMIT 1;`
- **ID 116 · car_1 · moderate**: What is the full name of each car maker, along with its id and how many models it produces?
  - Gold: `SELECT T1.FullName , T1.Id , count(*) FROM CAR_MAKERS AS T1 JOIN MODEL_LIST AS T2 ON T1.Id = T2.Maker GROUP BY T1.Id;`
  - Qwen: `SELECT cm.Id, cm.FullName, COUNT(ml.ModelId) AS ModelCount FROM car_makers cm JOIN model_list ml ON cm.Id = ml.Maker GROUP BY cm.Id, cm.FullName;`
- **ID 119 · car_1 · moderate**: Which distinctive models are produced by maker with the full name General Motors or weighing more than 3500?
  - Gold: `SELECT DISTINCT T2.Model FROM CAR_NAMES AS T1 JOIN MODEL_LIST AS T2 ON T1.Model = T2.Model JOIN CAR_MAKERS AS T3 ON T2.Maker = T3.Id JOIN CARS_DATA AS T4 ON T1.MakeId = T4.Id WHERE T3.FullName = 'General Motors' OR T4.weight > 3500;`
  - Qwen: `SELECT DISTINCT Model FROM model_list WHERE Maker IN ( SELECT Id FROM car_makers WHERE FullName = 'General Motors' ) UNION SELECT DISTINCT Model FROM car_names WHERE MakeId IN ( SELECT Id FROM cars_data WHERE Weight > 3500 );`

## Qwen wins over Llama

- **ID 395 · battle_death · moderate**: Show names, results and bulgarian commanders of the battles with no ships lost in the 'English Channel'.
  - Gold: `SELECT name , RESULT , bulgarian_commander FROM battle EXCEPT SELECT T1.name , T1.result , T1.bulgarian_commander FROM battle AS T1 JOIN ship AS T2 ON T1.id = T2.lost_in_battle WHERE T2.location = 'English Channel'`
  - Qwen: `SELECT battle.name, battle.result, battle.bulgarian_commander FROM battle WHERE battle.id NOT IN ( SELECT ship.lost_in_battle FROM ship WHERE ship.location = 'English Channel' );`
- **ID 466 · battle_death · simple**: What are the death and injury situations caused by the ship with tonnage 't'?
  - Gold: `SELECT T1.killed , T1.injured FROM death AS T1 JOIN ship AS t2 ON T1.caused_by_ship_id = T2.id WHERE T2.tonnage = 't'`
  - Qwen: `SELECT killed, injured FROM death WHERE caused_by_ship_id IN (SELECT id FROM ship WHERE tonnage = 't');`
- **ID 27 · car_1 · simple**: What is the minimum weight of the car with 8 cylinders produced in 1974 ?
  - Gold: `select min(weight) from cars_data where cylinders = 8 and year = 1974`
  - Qwen: `SELECT MIN(Weight) FROM cars_data WHERE Cylinders = 8 AND Year = 1974;`
- **ID 37 · car_1 · moderate**: What is the model for the car with a weight smaller than the average?
  - Gold: `SELECT T1.model FROM CAR_NAMES AS T1 JOIN CARS_DATA AS T2 ON T1.MakeId = T2.Id WHERE T2.Weight < (SELECT avg(Weight) FROM CARS_DATA)`
  - Qwen: `SELECT Model FROM car_names WHERE MakeId IN ( SELECT Id FROM cars_data WHERE Weight < (SELECT AVG(Weight) FROM cars_data) );`
- **ID 55 · car_1 · complex**: What are the countries having at least one car maker? List name and id.
  - Gold: `SELECT T1.CountryName , T1.CountryId FROM COUNTRIES AS T1 JOIN CAR_MAKERS AS T2 ON T1.CountryId = T2.Country GROUP BY T1.CountryId HAVING count(*) >= 1;`
  - Qwen: `SELECT CountryName, CountryId FROM countries WHERE CountryId IN (SELECT Country FROM car_makers);`

## Llama wins over Qwen

- **ID 150 · car_1 · simple**: What are the makers and models?
  - Gold: `SELECT Maker , Model FROM MODEL_LIST;`
  - Qwen: `SELECT Maker, Model FROM car_makers JOIN model_list ON car_makers.Id = model_list.Maker;`
  - SQLite error: `ambiguous column name: Maker`
- **ID 369 · car_1 · moderate**: For a volvo model, how many cylinders does the version with least accelerate have?
  - Gold: `SELECT T1.cylinders FROM CARS_DATA AS T1 JOIN CAR_NAMES AS T2 ON T1.Id = T2.MakeId WHERE T2.Model = 'volvo' ORDER BY T1.accelerate ASC LIMIT 1;`
  - Qwen: `SELECT Cylinders FROM cars_data WHERE Id = ( SELECT MakeId FROM car_names WHERE Make = 'volvo' ORDER BY Accelerate ASC LIMIT 1 );`
  - SQLite error: `no such column: Accelerate`
- **ID 372 · car_1 · moderate**: What is the average edispl of the cars of model volvo?
  - Gold: `SELECT avg(T2.edispl) FROM CAR_NAMES AS T1 JOIN CARS_DATA AS T2 ON T1.MakeId = T2.Id WHERE T1.Model = 'volvo';`
  - Qwen: `SELECT AVG(T2.Edispl) FROM car_names AS T1 JOIN cars_data AS T2 ON T1.MakeId = T2.Id WHERE T1.Make = 'volvo';`
- **ID 455 · car_1 · moderate**: For model volvo, how many cylinders does the car with the least accelerate have?
  - Gold: `SELECT T1.cylinders FROM CARS_DATA AS T1 JOIN CAR_NAMES AS T2 ON T1.Id = T2.MakeId WHERE T2.Model = 'volvo' ORDER BY T1.accelerate ASC LIMIT 1;`
  - Qwen: `SELECT Cylinders FROM cars_data WHERE Id = ( SELECT MakeId FROM car_names WHERE Model = 'volvo' ORDER BY Accelerate ASC LIMIT 1 );`
  - SQLite error: `no such column: Accelerate`
- **ID 623 · car_1 · moderate**: What is the name of the different car makers who produced a car in 1970?
  - Gold: `SELECT DISTINCT T1.Maker FROM CAR_MAKERS AS T1 JOIN MODEL_LIST AS T2 ON T1.Id = T2.Maker JOIN CAR_NAMES AS T3 ON T2.model = T3.model JOIN CARS_DATA AS T4 ON T3.MakeId = T4.id WHERE T4.year = '1970';`
  - Qwen: `SELECT DISTINCT cm.Maker FROM car_makers cm JOIN model_list ml ON cm.Id = ml.Maker JOIN cars_data cd ON ml.ModelId = cd.Id WHERE cd.Year = 1970;`

## Interpretation and next review

- Inspect representative SQL pairs above before assigning a cause. An executable mismatch can reflect a wrong join, grouping, filter, projection, literal, or a questionable gold annotation.
- Compare moderate/complex accuracy with the current annotated reference, then test one proposed lever at a time on the same IDs.
- Manually review question/gold inconsistencies. Never feed dev gold SQL or these failure labels into a prompt scored on Spider dev.
