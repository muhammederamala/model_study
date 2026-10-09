# Lever: execution_repair

- **Status:** planned; no implementation or results
- **`--lever=` value after implementation:** `execution_repair`

## Hypothesis

A single repair pass using a real SQLite error can recover invalid queries,
particularly the current `no such column` failures, at modest average cost
when applied only to queries that fail to execute.

## Planned implementation

Generate SQL as in the reference run, execute it read-only, and on a parse or
execution error give the model its SQL, the error, the question, and the same
schema. Allow one corrected query; retain both candidates and all timing.
Never pass gold SQL, expected rows, or `exec_match` to the repair prompt.
Do not treat an empty result as proof of an error.

## Evaluation and verdict

Compare against the reference on the same IDs. Report repaired-invalid count,
valid queries harmed, final execution accuracy by complexity, added calls, and
latency. Keep only if the measured recovery justifies the extra inference.
