# Evaluation insights

Failure analyses live here after a model finishes a complete, unique set of
1,032 Spider dev questions. Source predictions remain in `results/runs/`.

The first planned report is `qwen25coder_14b.md`. The script
`scripts/analyze_qwen14.py` generates it only after Qwen 14B and Llama have
results for the same complete question set. It summarizes paired outcomes,
complexity and SQL-construct accuracy, execution errors, and representative
query pairs for manual interpretation. The sequential runner invokes the
analysis before moving on to Qwen 7B. `scripts/watch_qwen14.py` can also wait
for a Qwen run started in an existing terminal and generate the report when
the result CSV reaches all 1,032 unique IDs.

The report is descriptive. Any proposed cause or lever needs a paired
experiment, and Spider dev gold SQL must stay out of prompts evaluated on
Spider dev.

After Qwen 14B finishes, [qwen25coder_14b_review.md](qwen25coder_14b_review.md)
records manually checked failure mechanisms and the separate output-column
order diagnostic. The automated report may be regenerated; keep reviewed
interpretation in this separate file.

For the ongoing grounded Qwen 14B comparison, run
`python3 scripts/audit_grounded_results.py` to produce a paired score under
`results/audits/grounded_qwen14b/`. Its README records the reviewed reference
corrections and the temporary `flight_2` whitespace normalization. Keep that
audited score separate from the saved strict Spider execution score.
