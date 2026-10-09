# Spider semantics JSON

One `<db_id>.json` file exists for each of the 166 databases in
`data/spider_data/tables.json`. Generate them with:

```bash
python3 scripts/build_semantics_json.py
```

The files use the requested `text_to_sql_semantics` shape. `entities` include
Spider's table and column labels, types, declared primary and foreign keys,
and observed low-cardinality text values and row counts from the matching
SQLite database. `terms` maps normalized table labels to physical table names.
`metrics` contains only table row counts, which need no business definition.

Spider provides no authoritative business glossary. For that reason,
`assumptions_to_confirm` and `example_interpretations` are empty, and the
files do not claim business metrics, status meanings, currencies, time zones,
or entity relationships absent from the schema. A domain expert can add
reviewed definitions later. Regenerating a file replaces manual edits, so
keep any reviewed additions separately until a merge workflow exists.

These JSON files are standalone artifacts. Neither the local Ollama runner
nor the cloud runner currently reads or sends them. The active 20-database
evaluation still uses `data/semantic_layer_dataonly/*.sql`.
