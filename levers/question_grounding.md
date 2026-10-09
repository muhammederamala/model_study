# Lever: question_grounding

- **Status:** completed; 788/1,032 on Spider dev (76.4%)
- **Output:** `results/runs/question_grounding/`

## Hypothesis

Selecting relevant tables, columns, join paths, and exact values for each
question will reduce wrong-column, wrong-join, and wrong-literal SQL. The
current static layer lists values for only low-cardinality text columns and
does not select context for the question.

## Implementation

`scripts/build_semantic_catalog.py` combines the existing machine-derived
semantics with observed SQLite text values for the 20 Spider dev databases.
`scripts/ground_question.py` matches a question to schema labels, value
candidates, and declared join paths without an Ollama call. It keeps ambiguous
value matches instead of choosing a filter column. `data/reviewed_semantics.md`
adds manually checked structural notes for each database. The current full
schema remains available so a bridge table is not accidentally removed. No
dev gold SQL is used for catalog construction or prompt context.

`scripts/run_grounded_eval.py` adds the notes and bounded candidate context to
the direct-SQL Qwen 14B prompt. It makes one model call per ID and saves a
resumable CSV plus paired comparison against the frozen baseline. Inspect the
prompt with `python3 scripts/run_grounded_eval.py --dry-run`; run a pilot with
`--max-new 10`, then complete the full set without that limit.

## Evaluation and verdict

Compare on identical Spider dev IDs against the current annotated reference,
especially questions with joins, literal filters, and missing-column errors.
Report moderate/complex accuracy, SQL error rate, prompt size, and latency.
The catalog is a structural v1, not an approved business glossary. Its strict
score was 788/1,032 (76.4%), compared with the frozen baseline's 808/1,032
(78.3%). The reviewed audit applies known `flight_2` whitespace normalization,
two question-reference corrections, and one unspecified-column-order rule to
both runs. Under that audit, catalog scored 820/1,032 (79.5%) and baseline
802/1,032 (77.7%), a paired net gain of 18. The raw strict and audited results
are both retained; see `../results/audits/grounded_qwen14b/summary.json` and
`../results/runs/question_grounding/comparison_qwen25coder_14b.json`.
