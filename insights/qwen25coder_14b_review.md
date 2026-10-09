# Qwen 2.5 Coder 14B: reviewed failure insights

Reviewed 2026-10-05 after all 1,032 Spider dev IDs were saved. The detailed
counts and representative SQL pairs are in [the generated report](qwen25coder_14b.md).
This review uses the same data-only annotated schema as the local baseline.
It describes Qwen's errors; it does not measure whether the annotations helped
because no paired plain-schema control exists.

## Result and where improvement came from

Qwen matched the gold result on **808/1,032 (78.3%)** questions, versus Llama
3.1 8B's **733/1,032 (71.0%)** on identical IDs: **+75 questions / +7.3
percentage points**. Qwen won 125 questions that Llama missed, while Llama won
50 that Qwen missed. Moderate improved from 205/364 (56.3%) to 246/364
(67.6%); complex improved from 94/171 (55.0%) to 111/171 (64.9%).

Qwen is stronger on the constructs that troubled Llama: JOIN 290/408 versus
238/408, and nested SELECT 106/159 versus 77/159. This is a *model*
comparison under the same schema, not evidence of a gain from semantics.

## The scorer flags many output-column permutations

I reran all 213 Qwen queries that executed successfully but failed the local
result comparison, then compared each predicted result with the gold result
under every output-column permutation of width 2–5. **49/213 mismatches**
returned the same multiset of rows after reordering columns: 7 simple, 30
moderate, and 12 complex. Examples: IDs **63** and **116** in `car_1`, **41**
in `world_1`, and **40** in `wta_1`. In ID 63, gold returns
`MAX(Accelerate), Cylinders`; Qwen returns `Cylinders, MAX(Accelerate)` with
the same grouped values.

The recorded **78.3% remains the primary local-run number**. If column order
were ignored for these 49 cases, this one-database diagnostic would be
857/1,032 (83.0%). That is a different scoring rule and could include
coincidental matches; it must not replace the main figure without a deliberate
metric decision. The remaining 175 mismatches comprise 11 SQLite execution
errors, 95 with a different number of result rows, 14 with a different number
of columns, and 55 with the same row/column count but different cell values.

## Substantive failure patterns

1. **Quantifier and negation logic.** ID 153 asks for a battle that lost both
   named ships; Qwen's `name IN (...)` accepts either ship, while gold uses an
   intersection. ID 127 asks for countries where English is *not* official;
   Qwen joins to English rows marked nonofficial, which omits countries with
   no such row and can include countries with both kinds of English row. ID
   179 asks for dogs whose treatment cost is not over 1,000; Qwen's inner join
   excludes dogs with no treatments, which the gold `NOT IN` includes.

2. **Join path and row granularity.** ID 950 joins `battle.id` directly to
   `death.caused_by_ship_id`, skipping the `ship` bridge table. ID 528 computes
   average dog age after joining to `Treatments`, so dogs with several
   treatments are counted several times; gold averages distinct dogs selected
   by an `IN` condition. These are executable queries, so a syntax-only repair
   pass would not catch them.

3. **Entity, column, and value grounding.** ID 53 looks for Anguilla in
   `city.Name` although it is a country in the database. ID 369 filters
   `car_names.Make = 'volvo'` instead of `car_names.Model`, and orders a
   subquery on `Accelerate`, a column absent from `car_names`. This illustrates
   why relevant table/column/value retrieval may help beyond a static schema.

4. **Aggregation target.** ID 152 sums `city.Population` while the question
   and gold query concern country population. ID 238 compares acceleration
   with `MAX(Horsepower)` instead of the acceleration of the car having the
   greatest horsepower. The SQL executes but answers a different question.

5. **Invalid SQL is a smaller slice.** Only **11/224** recorded mismatches are
   SQLite errors: 8 `no such column`, 3 `ambiguous column name`. Even perfect
   recovery of all 11 can add at most 1.1 percentage points to Qwen's current
   score. An error-triggered repair lever is still testable, but it is not the
   main route to moderate/complex gains for this model.

## Review cautions and next experiments

- ID **454** asks for battle *name, date, and result*, but its gold SQL selects
  only name and date; Qwen selects all three and is marked wrong. This is a
  concrete question/gold inconsistency for manual review, not proof that every
  mismatch is a label issue.
- The 1,032-question grader compares results on one SQLite instance and
  treats output-column order as significant. Keep that score for consistent
  model comparisons; report the permutation diagnostic separately.
- First run the planned plain-schema control on the same IDs to measure the
  contribution of semantics. For Qwen-specific improvement, prioritize the
  `query_planning` and `question_grounding` levers, then measure
  `execution_repair` and `few_shot_examples` separately. Use only database
  contents or training-split examples in prompts scored on Spider dev.
