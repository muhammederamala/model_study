# Lever: few_shot_examples

- **Status:** planned; no implementation or results
- **`--lever=` value after implementation:** `few_shot_examples`

## Hypothesis

A few relevant question-to-SQL examples can teach join, grouping, and nested
query patterns that static schema annotations do not explain.

## Planned implementation

Select examples only from Spider's training split or another source disjoint
from the evaluated questions. Use a fixed selection method and small prompt
budget; do not retrieve examples from Spider dev questions or gold SQL when
scoring Spider dev. Record selected example IDs to make runs reproducible.

## Evaluation and verdict

Compare against the same-model, same-question annotated reference. Measure
moderate/complex gains, regressions on simple questions, prompt tokens, and
latency. Keep only if the added context helps enough on the 16 GB CPU target.
