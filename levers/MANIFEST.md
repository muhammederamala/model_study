# Lever manifest

Each lever is one testable change to the text-to-SQL pipeline. A planned lever
has no results and is not implemented by merely passing its name to `--lever`:
that flag currently selects an output directory only. Implement the strategy
before running it, and keep each result set separate.

The current Spider dev reference uses database-derived annotations from
`data/semantic_layer_dataonly/` and writes to `results/runs/spider_baseline/`.
Llama 3.1 8B, Qwen 2.5 Coder 14B, and DeepSeek Coder V2 have completed 1,032 questions each; Gemma 2, Gemma 3, and Qwen 7B are partial and paused. There is no
same-question plain-schema result, so the annotations' effect is unmeasured.
The fuller layer in `data/semantic_layer/` includes patterns mined from Spider
dev answers: evaluate that variant only on held-out questions that did not feed
those patterns, such as `data/invented_eval.json` (noting its templated wording).

| # | Lever | Status | Hypothesis / purpose | Verdict |
|---|---|---|---|---|
| 0 | [baseline](baseline.md) | running | Current annotated Spider dev reference | pending |
| 1 | [plain_schema_control](plain_schema_control.md) | planned | Measure the annotations' actual effect | pending |
| 2 | [question_grounding](question_grounding.md) | wired; awaiting run | Add reviewed structural notes and relevant schema/value candidates to direct-SQL Qwen | pending |
| 3 | [execution_repair](execution_repair.md) | planned | Repair SQL that fails to execute | pending |
| 4 | [query_planning](query_planning.md) | planned | Improve joins, grouping, nested queries and set operations | pending |
| 5 | [few_shot_examples](few_shot_examples.md) | planned | Teach SQL patterns using training-split examples | pending |
| 6 | [sft_lora](sft_lora.md) | planned | Train one Qwen agent adapter per client from reviewed SQL building blocks and tool-use trajectories | pending |
| 7 | [json_compiler](json_compiler.md) | ready to run | Compare Qwen JSON plans compiled to SQLite against its frozen SQL baseline on all Spider dev IDs | pending |
| 8 | [english_semantics](english_semantics.md) | completed | Compare readable English presentation of retrieved semantic facts against the semantic catalog format | English audited score trails catalog by 9 |

Historical: [semantic_layer](semantic_layer.md) was originally lever 1, then
merged into the annotated baseline before a full comparison. It is retired as
a separate run; the plain-schema control above restores the missing comparison.

## Evaluation sequence

1. Finish and freeze the current reference CSVs. Record model, question IDs,
   prompt/schema variant, accuracy by complexity, and average latency.
2. Run the plain-schema control on the **same** Spider dev question IDs and
   model, using `schema_text` from `data/eval_sample.json`. Compare paired
   outcomes; this is a measurement control, not a candidate improvement.
3. For each improvement lever, first use a fixed pilot containing moderate and
   complex questions. Compare on identical IDs against the current best with
   one change at a time. Expand promising changes to the full set and other
   models. Preserve failed experiments and their verdicts.
4. Keep Spider dev gold SQL and any patterns mined from it out of prompts for
   Spider dev evaluation. Use training-split demonstrations or database data.
   Repair may use SQLite errors, never the gold answer or `exec_match`.
5. Report execution accuracy, moderate/complex accuracy, SQL error rate, and
   latency. Manually review a sample of mismatches because a single-database
   execution comparison and occasional question/gold inconsistencies can
   misstate semantic correctness.

Full numbers belong in `results/runs/<lever>/summary.json` and
`results/progress_log.csv` after a run. Update each lever's writeup and this
manifest when its evaluation and verdict are ready.

**Qwen 14B evidence (2026-10-05):** the completed run reached 808/1,032
(78.3%), with 246/364 moderate and 111/171 complex correct. Only 11 of its
224 recorded mismatches were SQL execution errors; most proposed gains need
better question grounding or query logic, not syntax repair alone. See the
[reviewed insights](../insights/qwen25coder_14b_review.md). The plain-schema
control remains necessary before attributing any gain to semantics.

## Roadmap toward 90% on this local Spider dev score

The target is at least 929/1,032 correct, **121 more** than Qwen 14B's current
808. If its 451 simple successes stay fixed, moderate and complex together
must rise from 357/535 (66.7%) to 478/535 (89.3%). Perfect repair of the 11
SQLite errors adds at most 1.1 points. An impossible oracle that knows which
answer is right among the three complete models (Qwen 14B, Llama 8B, DeepSeek
Coder V2) reaches only 882/1,032 (85.5%) from their current outputs. A new
strategy or model must solve cases all three currently miss.

Prioritize the following, measuring paired wins and losses against Qwen on a
fixed moderate/complex pilot and then the full dev set:

1. Audit the grader and 49 output-column permutation cases. Preserve the
   existing score; report any alternate metric separately. This is measurement
   work, not a model improvement.
2. Test question-specific schema, join-path, and exact-value grounding using
   database contents only. Focus on wrong columns, missing bridge tables, and
   value mismatches without hiding needed schema items.
3. Test query planning and semantic verification for joins, negation,
   quantifiers, aggregation grain, and nested comparisons. A query that merely
   executes is not necessarily correct, so syntax-only repair cannot address
   most failures. Count added calls and end-to-end latency.
4. Test retrieved few-shot examples from Spider **train** only; never use dev
   gold SQL in a prompt evaluated on dev. If prompt-only gains remain small,
   evaluate a stronger model. The [per-client LoRA plan](sft_lora.md) is a
   separate agent deployment experiment using each client's reviewed SQL
   building blocks and tool-use trajectories; Spider train databases can
   simulate clients for a method check.

The machine-derived JSON files in `data/semantics_json/` are currently unwired
and contain no reviewed business metrics. They cannot explain or improve the
current benchmark score until a separate prompt strategy is implemented and
tested. For a production database, obtain confirmed metric definitions and
evaluate on held-out real user questions as well as Spider.
