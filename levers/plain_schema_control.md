# Lever: plain_schema_control

- **Status:** planned; no implementation or results
- **`--lever=` value after implementation:** `plain_schema_control`

## Hypothesis

The database-derived annotations may improve execution accuracy, especially
where literal values or unusual foreign keys matter. A paired plain-schema
run is needed to measure that effect; this control is not an improvement by
itself.

## Planned implementation

Add a schema-source option to `run_eval.py` so this run sends each example's
original `schema_text` while retaining the same model, prompt wording, SQL
extraction, question IDs, and grader as `spider_baseline`. Keep output separate.
`--lever` alone does not currently change the schema source.

## Evaluation and verdict

Start with Llama 3.1 8B on a fixed moderate/complex pilot, then use all 1,032
Spider dev IDs for a reliable paired comparison. Count questions gained and
lost as well as the net accuracy difference by complexity and latency. Do not
compare against the deleted 149-question sample. Record whether the
annotations helped, hurt, or were inconclusive here.
