# JSON plan and SQLite compiler

## Hypothesis

Constrained JSON plans may reduce invalid SQL and make table, column, and value validation deterministic. They can also fail when the plan grammar cannot express a Spider query or Qwen emits an unsupported shape.

## Implementation

`scripts/run_json_eval.py` prompts the same base Qwen 2.5 Coder 14B model once per Spider dev question, using the data-only semantic schema. `scripts/json_sql_compiler.py` validates the JSON plan against the live SQLite catalog and compiles a read-only SELECT with bound literal values. Invalid JSON, compilation failures, and SQL errors count as wrong answers. The response cap is 1,100 tokens, versus 300 for the SQL baseline.

Run `python3 scripts/run_json_eval.py --max-new 10` for a pilot, then `python3 scripts/run_json_eval.py` for all remaining IDs. Output is isolated in `results/runs/json_compiler/`; the frozen SQL baseline is read only. Each saved row updates a paired comparison with recovered and regressed IDs. Run only one local Ollama evaluator at a time.

## Results and verdict

Pending a live full run. Report full-set and complexity-level accuracy, compile and execution failures, paired wins and losses, and latency before accepting or rejecting this lever. This experiment does not train an adapter or run a multi-query agent.
