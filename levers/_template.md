<!-- Copy this file to levers/<lever_name>.md when starting a new lever. -->

# Lever: <name>

- **Status:** planned | drafted, not active | running | evaluated, pending verdict | accepted | rejected
- **Started:** YYYY-MM-DD
- **`--lever=` flag value:** `<name>`

## Hypothesis

What are we changing, and why do we expect it to move accuracy? One or two sentences, written *before* results come in.

## Implementation

What actually changed — which script, which flag, what the prompt/schema/model looks like differently from the previous lever. Link the relevant file(s).

## Models tested

- [ ] llama31_8b
- [ ] gemma2_9b
- [ ] qwen25coder_7b
- [ ] sqlcoder_7b
- [ ] qwen25coder_14b
- [ ] gemma3_12b
- [ ] deepseekcoderv2_16b

## Results

Pull from `results/runs/<name>/summary.json` / `results/progress_log.csv` once `aggregate.py <name>` has run.

| Model | Overall | Simple | Moderate | Complex | vs previous lever |
|---|---|---|---|---|---|
| ... | | | | | |

## Verdict

**Accepted / Rejected / Inconclusive** — the actual decision, and the reasoning. If rejected, say why (didn't help, helped but not enough to justify the cost, broke something else, etc.) rather than just deleting the lever — the negative result is worth keeping on record.
