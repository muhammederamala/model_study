# Grounded Qwen 14B score audit

Run `python3 scripts/audit_grounded_results.py` from the repository root to refresh `summary.json` and `per_question.csv`. The script reads the saved baseline and grounded SQL, scores only IDs present in both runs, and records SHA-256 hashes of its inputs. It does not call Ollama or change either run's CSV. Rerun after the grounded evaluation finishes to obtain the full 1,032-question comparison.

The **strict** columns reproduce the saved execution-match flags. The **audited** columns apply these same rules to both runs:

- `flight_2_whitespace_normalized`: Copy `flight_2.sqlite` into memory, trim known padded airport and flight text fields, and trim quoted SQL literals in both the gold and predicted queries before executing them. The live SQLite file is unchanged. This addresses joins and filters affected by whitespace inside the database. The evaluator already strips whitespace from returned cells.
- `corrected_reference`: For ID 454, compare all three requested battle fields (`name`, `date`, `result`). For ID 997, rank ships by the sum of `death.injured` rather than the number of death records. These corrections were checked against the question and schema.
- `unspecified_column_order`: For ID 63, accept either order of the two requested result columns. Row multiplicity and values must still match.

All other questions keep their strict score. The audited score is a targeted interpretation of known data and reference issues, **not an official Spider metric or a complete review of every apparent false negative**. Some strict successes become audited failures when normalized data exposes a real query difference. Inspect `per_question.csv` for changed IDs and query errors; keep both score columns when comparing models.
