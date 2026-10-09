# Spider 2.0 — future track (not started)

This folder is a placeholder, kept deliberately separate from the main Spider 1.0
pipeline in `../scripts/` and `../data/`. **Nothing in here runs yet.** It exists so
the Spider 2.0 track has a home when we pick it up, without touching the working
Spider 1.0 setup.

## Why it's separate

Spider 2.0 is architecturally a different kind of eval, not a bigger dataset:

| | Spider 1.0 (`../scripts/`) | Spider 2.0 (here, future) |
|---|---|---|
| Shape | 1 question → 1 SQL query, graded once | agentic: model gets a live environment (DB access + docs/code files), takes multiple turns (run a query, see the result, iterate), submits a final answer that can itself be several queries or file edits |
| Engine | SQLite only, fully local | Spider2-Snow/Lite need real BigQuery/Snowflake accounts (not offline); only **Spider2-DBT** (DuckDB, 69 tasks) is local/offline-compatible |
| Harness | single prompt → single response → grade | needs a tool-use loop: give the model SQL execution + file read/write, let it take several turns before grading |
| Difficulty | strong models hit 85%+ | frontier models score ~10-17% — designed to be far from solved |

Source: https://spider2-sql.github.io/ and https://github.com/xlang-ai/Spider2
(Spider2-DBT README confirms tasks can need SQL "sometimes over 100 lines" —
not single-query-shaped like Spider 1.0.)

## Scope when we start this

Recommended starting point: **Spider2-DBT only** (69 DuckDB tasks), since it's the
only subset that fits this project's constraints (offline, CPU, no cloud account).
Spider2-Snow/Lite would need Snowflake/BigQuery credentials and network access,
which breaks the fully-local setup described in `../CLAUDE.md`.

## What building this out will actually require (not done yet)

1. **A tool-use loop in `run_eval.py`-equivalent** — the model needs to call
   SQL-execute / file-read actions across multiple turns before submitting a final
   answer, unlike the current single-shot `query_model()` → `run_sql()` pattern.
2. **A different grader** — comparing final DuckDB table state (post dbt build)
   against gold, not a single query's row-multiset like `rows_match()`.
3. **The Spider2 repo's DBT project files** (dbt models, `schema.yml`, sources) —
   not yet downloaded into `data/` here.
4. Realistic expectation-setting: even frontier models score ~10-17% on the full
   benchmark; the small CPU-run models in this study (7-9B) should be expected to
   score much lower, possibly near 0%. This track is for stretching/probing
   headroom, not for chasing a target accuracy the way Spider 1.0 is.

## When to pick this up

Once Spider 1.0 accuracy work (`../scripts/`, `../results/`) has run its course —
i.e. once further prompt/model tuning stops moving the needle there.
