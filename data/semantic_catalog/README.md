# Source-grounded semantic catalog

`scripts/build_semantic_catalog.py` generates one JSON file for each of the 20 Spider dev databases. It combines the existing `data/semantics_json/<db_id>.json` metadata with observed text values from the matching SQLite database. Each file contains entities, columns, declared foreign-key relationships, schema labels, and a bounded value index. It reads **no Spider questions or gold SQL**.

The catalog is machine-derived. Table and column labels are hints, not approved business definitions. Spider primary-key metadata is retained as a declaration, but row grain is omitted because some declared keys are duplicated in the SQLite rows. A value match means a string occurs in a column; it does not prove that the column is the correct filter for a question. Columns with more than 25,000 distinct values would be listed in `skipped_high_cardinality_columns`; none were skipped in this 20-database snapshot. Catalogs are generated artifacts; keep reviewed interpretations in a separate source so rebuilding does not erase them.

The manually authored [structural review](../reviewed_semantics.md) records row-grain corrections, undeclared but observed joins, and data quirks across all 20 databases. It is kept separate from generated JSON and included in the grounded Qwen runner's prompt. It is a structural v1 review, not an approved business glossary.

**Benchmark readiness:** This catalog plus the reviewed notes is the frozen input for the first grounded Spider comparison. A fast audit checked all 20 catalog files against their SQLite tables and columns, all 63 declared join edges, all 33,501 indexed values' column references, and prompt construction for all 1,032 evaluation questions. No high-cardinality columns were skipped; 12 questions produced no lexical or value match and use the full schema fallback. The runner hashes these inputs in its run manifest and refuses to append if they change. This establishes input completeness, not SQL accuracy or recall of every useful semantic relation.

Build or preview without contacting Ollama:

```bash
python3 scripts/build_semantic_catalog.py
python3 scripts/ground_question.py --id 153
python3 scripts/ground_question.py --db-id world_1 --question "Which continent is Anguilla in?"
```

`ground_question.py` reads the catalog and reviewed notes at request time. It matches question wording to schema labels and observed values, then includes declared join paths between matched tables. It preserves ambiguous matches as candidates. `scripts/run_grounded_eval.py` sends that context alongside the full data-only schema to Qwen and requests **direct SQL**. Run `--dry-run` to inspect the prompt, `--max-new 10` for a resumable pilot, and then without a limit for the full comparison. Grounded results go only to `results/runs/question_grounding/`; accuracy is not established until those IDs are evaluated.
