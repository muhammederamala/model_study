# Lever: baseline

- **Status:** running
- **Started:** 2026-09-29 (redefined same day — see below)
- **Active Spider dev result folder / `--lever=` value:** `spider_baseline`

## Hypothesis

N/A as an accuracy-improvement attempt — this is the reference point every future lever is measured against. **But note what it actually contains, which changed mid-day:**

**Original plan:** plain `schema_text` (bare `CREATE TABLE` strings, no annotations), as a true zero-enrichment reference point, with `semantic_layer` as a separate lever to compare against it.

**Revised same day:** given the full 1032-question × 7-model run takes ~22 hours (even after a CPU governor fix cut it from ~38h), running the plain-schema version first — knowing it would immediately be superseded by the semantic-layer version — wasn't worth the time. Decision: **skip the plain-schema-only run entirely, and start the baseline directly from the semantic-layer-annotated schema.** So "baseline" now means what `levers/semantic_layer.md` used to describe: inline sample values + auto-detected FK quirks, not bare schema.

**Consequence:** we don't have a same-scale (N=1032, 20 dbs) plain-schema number to compare against. The old 149-question sample's plain-schema results existed but were deleted in the earlier N=1032 reset (see CLAUDE.md Changelog, 2026-09-29 entries) and aren't directly comparable anyway (different N, different db coverage, and were pre-CPU-governor-fix so latency isn't comparable either). If a clean plain-vs-semantic comparison is ever needed, it would have to be re-run from scratch as its own lever.

## Implementation

For `--dataset=dev`, `run_eval.py` reads `data/semantic_layer_dataonly/<db_id>.sql` for the prompt's schema section, falling back to plain `schema_text` only if a semantic file is missing. All 20 dev databases are covered. This variant uses database-derived annotations only: real low-cardinality values, ranges, row counts, and auto-detected FK quirks. The fuller `data/semantic_layer/` files contain patterns mined from dev answers and are reserved for evaluation on held-out questions.

## Models tested

- [x] llama31_8b (1,032/1,032)
- [ ] gemma2_9b (paused at 177/1,032 after ~49-second median latency)
- [ ] qwen25coder_7b (paused at 209/1,032)
- [ ] sqlcoder_7b
- [x] qwen25coder_14b (1,032/1,032)
- [ ] gemma3_12b (paused after ~75-second median latency on its first 19 questions)
- [x] deepseekcoderv2_16b (1,032/1,032)

(Run in batches of 250 per the user's instruction — a single 1032-question run per model would take a couple hours uninterrupted even post-CPU-fix.)

## Results

Llama, Qwen 14B, and DeepSeek Coder V2 are complete. Gemma 2, Gemma 3, and Qwen 7B have partial results and are paused. DeepSeek's full run confirms fast inference but lower accuracy, especially on moderate and complex questions. Aggregate only after the roster finishes; `results/runs/spider_baseline/summary.json` does not yet exist.

| Model | Overall | Simple | Moderate | Complex | vs previous lever |
|---|---|---|---|---|---|
| Llama 3.1 8B | 733/1032 (71.0%) | 434/497 (87.3%) | 205/364 (56.3%) | 94/171 (55.0%) | reference |
| Qwen 2.5 Coder 14B | 808/1032 (78.3%) | 451/497 (90.7%) | 246/364 (67.6%) | 111/171 (64.9%) | +7.3 points vs Llama |
| DeepSeek Coder V2 16B | 711/1032 (68.9%) | 440/497 (88.5%) | 192/364 (52.7%) | 79/171 (46.2%) | -9.4 points vs Qwen 14B |

DeepSeek median latency was 4.0 seconds/question versus Qwen's 14.2 seconds/question over the full 1,032. On identical questions, DeepSeek solved 43 that Qwen missed, while Qwen solved 140 that DeepSeek missed. DeepSeek had 30 recorded SQL execution errors versus Qwen's 11.

## Verdict

N/A — reference lever, not itself accepted/rejected. Every future lever's verdict is "did it beat this." (Whether the semantic-layer annotations *themselves* helped vs. plain schema is now an open question this baseline can't answer — see Hypothesis above.)
