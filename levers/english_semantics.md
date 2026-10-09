# Lever: english_semantics

- **Status:** completed; 811/1,032 audited (78.6%)
- **Output:** results/runs/english_semantics/
- **Model:** Qwen 2.5 Coder 14B
- **Dataset:** same 1,032 Spider dev IDs as the completed catalog run

## Hypothesis

Presenting question-matched schema and value clues in readable English may help
Qwen use them more effectively than a compact, catalog-style list.

## Controlled comparison

The runner reuses the catalog experiment's question-to-schema/value retrieval,
reviewed structural notes, full data-only schema, model settings, and grader.
It changes only how the selected facts are phrased. Names needed to write SQL
remain exact schema names. No Spider dev gold SQL is used to build the context.

Preview with `python3 scripts/run_english_semantics_eval.py --dry-run`, then use
`--max-new 10` for a pilot or omit it to complete all remaining IDs. The runner
resumes safely and reports strict paired scores. After each batch, run
`python3 scripts/audit_semantic_variants.py` to apply the reviewed audit rules
to the shared IDs across baseline, catalog, and English results.

## Results and verdict

The full run scored 789/1,032 (76.45%) strict and 811/1,032 (78.59%) under the
reviewed audit. Mean model latency was 25.3 seconds per question. The semantic
catalog scored 788/1,032 (76.36%) strict and 820/1,032 (79.46%) audited; the
baseline scored 808/1,032 (78.29%) strict and 802/1,032 (77.71%) audited.

On the audited metric, English recovered 7 catalog misses and regressed 16
catalog successes, for a net difference of -9 questions (-0.87 percentage
points). By complexity, English scored 446/497 simple, 252/364 moderate, and
113/171 complex, versus catalog's 452, 252, and 116. Thus readable wording
matched the catalog closely on strict accuracy but did not retain its audited
gain. The audit applies known whitespace normalization, reviewed reference
corrections, and the unspecified-column-order rule equally to all variants.
Full results: `../results/runs/english_semantics/comparison_qwen25coder_14b.json`
and `../results/audits/semantic_variants/summary.json`.
