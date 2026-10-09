# Lever: query_planning

- **Status:** planned; no implementation or results
- **`--lever=` value after implementation:** `query_planning`

## Hypothesis

Explicitly choosing result columns, joins, filters, grouping, and subquery or
set-operation structure before SQL generation may improve moderate and complex
questions, where the current one-shot prompt often returns executable but
incorrect SQL.

## Planned implementation

Test a structured intermediate plan followed by SQL generation, or a compact
single-call prompt that asks for the plan internally. Apply a fixed variant
across the pilot; do not tune against dev gold answers. Keep schema and
question IDs identical to the reference, and measure extra tokens/calls.

## Evaluation and verdict

Break out join, GROUP BY/HAVING, nested SELECT, and UNION/INTERSECT/EXCEPT
questions. Compare paired execution accuracy, simple-question regressions,
and latency. Accept only a repeatable gain with a viable CPU cost.
