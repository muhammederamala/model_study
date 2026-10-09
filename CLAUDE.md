# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
**Keep this file current** — whenever a structural or behavioral change is made (new lever, new model, new script argument, dataset rebuilt, results reset), update the relevant section here and add a dated entry to the Changelog at the bottom. Don't wait to be asked.

## What this is

A text-to-SQL system benchmark: local pipelines use open-weight models through Ollama on CPU-only hardware, while a deployed pipeline is evaluated through a cloud endpoint. The goal is to improve the complete pipeline, including semantic context, retrieval, planning, generation, and validation, rather than select a model by itself. The cloud endpoint path is documented in `cloud/README.md`. Not a git repository — a standalone scratch project.

For a project overview, evaluation flow, completed model results, and the planned Lambda comparison, see `ARCHITECTURE.md`.

The study is structured as a **baseline plus a sequence of accuracy-improvement "levers"** (e.g. richer schema prompting, self-consistency, bigger models), each evaluated against the same fixed question set so results are comparable across levers over time. See "Levers / results structure" below.

## Environment

### Git sharing and clone setup

See `README.md` for onboarding and proposed ignore rules, and `data/README.md` for the dataset layout. The agreed policy is to download Spider after cloning: do not commit the full archive, extracted source databases, caches, or duplicate copies. Keep code, fixed evaluation questions and pilot splits, semantic schemas/catalogs, reviewed notes, and small study results in Git. Local environments, credentials, logs, Python caches, and model weights should be ignored.

As of 2026-10-09, `.gitignore` and `requirements.txt` are present; the latter declares `requests>=2.31,<3`, the only imported external runtime dependency. A usable Git repository and dataset download script are still pending. Clone portability also requires replacing hardcoded project roots and absolute `sqlite_path` fields in evaluation/pilot files. Download setup must verify an exact archive checksum and reuse fixed IDs/splits rather than rebuild them. Those setup tasks remain pending.

### Existing development machine

- No GPU. Inference runs on CPU via Ollama (`ollama serve`, installed at `/usr/local/bin/ollama`, running as a systemd service under a dedicated `ollama` system user).
- Models live under `/usr/share/ollama/.ollama/models/` (root-owned; needs `sudo` to inspect directly — prefer `ollama list` / `ollama ps` instead).
- Python has no system `pip` (`ensurepip` is stripped on this Ubuntu image); it was bootstrapped via `get-pip.py` (kept in `tools/`) into `~/.local`. Use `python3 -m pip install --user ...` or plain `pip3` if already on PATH.
- Python deps actually used by `scripts/`: `requests` (HTTP calls to Ollama), `openpyxl` (installed later, ad hoc, for one-off `.xlsx` exports of results — not used by any script in `scripts/`). (`huggingface_hub` was used once, ad hoc, to fetch the dataset — see below.)
- **This dev box has ~24GB RAM**, but models are chosen against a **16GB target — the eventual cloud deployment budget, not a limit of this machine.** Don't let the extra local headroom justify pulling something that wouldn't fit 16GB; treat ~10-11GB as the realistic safe footprint per model once serving overhead is accounted for.

## Commands

```bash
# 1. Rebuild the eval set — currently targets the FULL Spider dev split (all 20 dbs,
#    SAMPLE_SIZE=1034 in the script), not a small sample. Only rerun if intentionally
#    changing scope; this regenerates data/eval_sample.json from scratch.
python3 scripts/prepare_dataset.py

# 2. Evaluate one model against Spider dev, in resumable batches.
#    Always pass both flags: the current defaults are dataset=invented and lever=baseline.
#    --lever chooses an output folder only; it does not implement a strategy.
python3 scripts/run_eval.py <ollama_model_name> <output_suffix> [batch_size] --dataset=dev --lever=spider_baseline
# e.g. python3 scripts/run_eval.py qwen2.5-coder:7b qwen25coder_7b 250 --dataset=dev --lever=spider_baseline
# writes/appends to results/runs/<lever>/results_<output_suffix>.csv

# 3. Aggregate all completed results/runs/<lever>/results_*.csv into that lever's summary.json,
#    and append a row per model to the master results/progress_log.csv.
python3 scripts/aggregate.py spider_baseline

# Resume the entire Spider dev roster sequentially, with a 3-minute heartbeat:
python3 scripts/run_all_models.py

# Probe one model with at most 10 new answers before deciding whether to continue:
python3 scripts/run_all_models.py --only deepseekcoderv2_16b --max-new 10
```

The cloud Lambda track is separate: `python3 scripts/run_cloud_eval.py --run <run> --label <model_label> --dry-run` previews its first Spider request. See `cloud/README.md` before supplying the teammate's endpoint and response contract. Cloud results live under `results/cloud/` and do not enter the local lever aggregate.

To rebuild the source-grounded index for the 20 Spider dev databases, run `python3 scripts/build_semantic_catalog.py`. Preview question-specific matches with `python3 scripts/ground_question.py --id 153` or pass `--db-id` and `--question`. This reads metadata and SQLite values only; it does not call Ollama or inspect dev gold SQL. `data/reviewed_semantics.md` is a separate manually authored structural review that corrects misleading key/grain hints and records observed data quirks. The separate grounded Qwen runner sends these notes and selected catalog candidates alongside the full data-only schema and asks for SQL directly. Preview with `python3 scripts/run_grounded_eval.py --dry-run`, run a resumable pilot with `--max-new 10`, then run without a limit for all 1,032 IDs. Its CSV and paired comparison stay under `results/runs/question_grounding/`; the baseline remains untouched. See `data/semantic_catalog/README.md`.

The grounded Qwen 14B catalog comparison completed 1,032 Spider dev IDs at 788/1,032 (76.4%) strict and 820/1,032 (79.5%) under the reviewed audit, versus baseline 808/1,032 (78.3%) strict and 802/1,032 (77.7%) audited. The plain-English context variant also completed: 789/1,032 (76.5%) strict and 811/1,032 (78.6%) audited, with 25.3 seconds mean latency. The audit normalizes known `flight_2` whitespace issues and applies the reviewed reference/order corrections equally to all three runs. The runner uses the same retriever, schema, model settings, and question IDs as the catalog run; only the presentation of additional context changes. Results are in `results/runs/english_semantics/`; run `python3 scripts/audit_semantic_variants.py` to refresh the paired audit at `results/audits/semantic_variants/`.

To retry **only Qwen 14B's 224 failed Spider dev IDs** with question-matched database values, an explicit query plan, and one SQLite-error repair attempt, run `python3 scripts/retry_qwen_failures.py`. Use `--dry-run` to inspect the first question without Ollama, or `--max-new 10` for a short resumable batch. It prints the current ID and stage, with a heartbeat every 15 seconds while Ollama is responding; the first model load can take time. Completed IDs are saved immediately, so rerunning after Ctrl+C resumes the interrupted ID. Results go to `results/retries/qwen25coder_14b_failed.csv` and a sibling summary JSON; the baseline CSV is untouched. The summary adds recovered IDs to the 808 baseline successes, but this selected-failure experiment is diagnostic, not a fair full-set score for a new strategy. Output-column permutations are reported separately and do not count as exact matches.

For a faster alternative, run `python3 scripts/retry_qwen_failures.py --single-call --max-new 10`. It asks for SQL in one request, retaining database-value grounding and error-triggered repair. It writes to a separate `results/retries/qwen25coder_14b_failed_single_call.csv` and summary so outcomes cannot mix with the two-stage version. Stop any active retry process before starting the other variant; concurrent Qwen requests on this CPU-only machine contend for memory and CPU.

For a direct full-set comparison of Qwen 14B SQL generation versus JSON-plan generation plus deterministic SQLite compilation, run `python3 scripts/run_json_eval.py`. It uses the same 1,032 Spider dev IDs and data-only schema, makes one Ollama call per ID, writes to `results/runs/json_compiler/results_qwen25coder_14b.csv`, and updates `comparison_qwen25coder_14b.json` after each row. `--max-new 10` runs a resumable pilot; `--dry-run` previews the prompt without contacting Ollama. Run only one local evaluator at a time. Invalid JSON, unsupported plans, and execution errors count as failures; request failures stop the run without saving that ID. The SQL baseline CSV is read only. This is a prompt/output-format experiment on the base Qwen model, not an SFT/LoRA result. JSON mode allows a longer response cap (1,100 tokens versus the SQL run's 300), so compare accuracy and latency with that limit in mind.

Pull a model before evaluating it: `ollama pull <model>` (e.g. `ollama pull llama3.1:8b`).

**Run only one `run_eval.py` at a time.** Two models loaded concurrently on this box causes heavy swap/CPU contention and per-query latency degrades ~5-10x. `ollama ps` shows what's currently loaded. (Also worth knowing: even a *single* model's measured latency can be skewed if something else is hogging CPU at the same time — e.g. several GUI apps, or a leftover background process — so treat any one latency/throughput number as approximate, not a precise benchmark, unless the box was otherwise idle.)

### Batching & resume (added once the eval set grew to 1032 questions)

At CPU inference speeds, running all ~1032 questions against one model in a single sitting can take several hours. `run_eval.py` supports resumable batches instead of one long run:

- Results always **append** to the same `results_<suffix>.csv` — never overwritten.
- Questions already present in that file (matched by `id`) are **automatically skipped**, so re-running the exact same command just continues with the next not-yet-done batch. No separate files per batch, no duplicate rows, no manual index bookkeeping.
- `batch_size` is optional — omit it to process everything remaining in one run.
- Example: `python3 scripts/run_eval.py llama3.1:8b llama31_8b 250 --dataset=dev --lever=spider_baseline` run repeatedly processes all 1032 in chunks of 250.

## Levers / results structure

Results are organized by **lever** — a named prompting/model strategy — so accuracy is comparable across strategies and over time, not just a single snapshot:

```
results/
  runs/
    spider_baseline/          <- active Spider dev run: database-derived annotations
      results_<suffix>.csv
      summary.json
    <future_lever>/            <- separate results after that strategy is implemented
      ...
  progress_log.csv            <- master append-only log, one row per (date, lever, model) aggregation:
                                  accuracy, per-bucket accuracy, exec_error_rate, avg_latency_sec.
                                  This is THE file for "did lever N beat lever N-1" across the whole study.
```

**`levers/` holds the human-readable narrative on top of that raw data** — `levers/MANIFEST.md` is the index (one row per lever: status, started date, verdict), and each lever has its own `levers/<name>.md` (hypothesis, what changed, results table, and — critically — the accept/reject verdict with reasoning, not just numbers). `levers/_template.md` is the starting point for a new one. **Update the manifest + that lever's `.md` every time a lever's evaluation completes** — the raw CSVs alone don't record *why* a lever was accepted or rejected, only what the numbers were.

The per-model `results_<suffix>.csv` files under each lever ARE the human-review export — no separate human-eval file is generated. Columns: `id, db_id, complexity_bucket, question, gold_sql, pred_sql, raw_response, exec_error, exec_match, latency_sec`.

**2026-09-29 reset:** the original 149-question sample's results were deleted (superseded) when the eval set was rebuilt to the full 1032-question dev split. The active annotated Spider dev run is in `results/runs/spider_baseline/`. The old sample cannot serve as a plain-schema control.

## Semantic layer (included in the current reference)

`scripts/build_semantic_schema.py --all-eval-sample` generates two variants. `data/semantic_layer_dataonly/<db_id>.sql` is used for `--dataset=dev` and adds database-derived annotations (no invented business prose):
- Real sample values for low-cardinality TEXT columns, pulled from the actual sqlite data (targets literal-value mismatches like a model producing `'Bachelors'` where gold used `'Bachelor'`).
- Numeric ranges, row counts, and auto-detected schema quirks: FK type mismatches and FKs joining to a non-primary-key column.

Annotations are inline SQL comments in the same `CREATE TABLE` style as the existing schema string (inline placement chosen deliberately — research on smaller models finds inline annotations help more than a separate documentation block).

`data/semantic_layer/<db_id>.sql` additionally contains usage patterns mined from Spider dev gold SQL, so `run_eval.py` uses it only for `--dataset=invented`. There is no same-question plain-schema comparison yet. The retired standalone semantic-layer lever and proposed control are documented in `levers/`.

`scripts/build_semantics_json.py` generates standalone `data/semantics_json/<db_id>.json` files for all 166 Spider schemas. These carry source-grounded table/column labels, keys, observed low-cardinality text values, row counts, and structural row-count metrics. They deliberately leave business assumptions and example interpretations empty pending domain review. See `data/semantics_json/README.md`. No evaluation or cloud runner reads these JSON files yet.

## Lever manifest

`levers/MANIFEST.md` is the index of every lever tried, its status, and its accept/reject verdict — start there before `progress_log.csv`'s raw numbers. Each lever also has its own `levers/<name>.md` with the hypothesis and reasoning behind the verdict, not just the accuracy delta.

Planned next levers: plain-schema control, question-specific schema/value grounding, execution-error repair, query planning, and training-split few-shot examples. Per-client supervised fine-tuning with LoRA is a separate agent deployment plan: one adapter per client trained on reviewed SQL building blocks and tool-use trajectories, so the agent can decompose a question, run bounded read-only SQL calls, interpret results, and answer. Spider train databases can simulate clients for checking the method. These remain documented plans only; `--lever` currently changes the output directory and does not implement a strategy.

## Model roster

`MODELS` dict in `scripts/aggregate.py` maps suffix → display name; add new entries there when adding a model.

| Suffix | Ollama name | Size | Notes |
|---|---|---|---|
| `llama31_8b` | `llama3.1:8b` | 4.9GB | Meta skipped this size class since — 3.2 only ships 1B/3B, 3.3 jumps to 70B. Nothing newer fits. |
| `gemma2_9b` | `gemma2:9b` | 5.4GB | Superseded by `gemma3_12b`; kept for the trend line. |
| `qwen25coder_7b` | `qwen2.5-coder:7b` | 4.7GB | Superseded by `qwen25coder_14b`; kept for the trend line. |
| `sqlcoder_7b` | `sqlcoder:7b` | 4.1GB | Defog hasn't updated this in ~2 years; still the newest that fits (15b variant needs ~16GB alone, no headroom left — excluded). |
| `qwen25coder_14b` | `qwen2.5-coder:14b` | 9.0GB | Added 2026-09-28: same-gen upgrade over the 7b. |
| `gemma3_12b` | `gemma3:12b` | 8.1GB | Added 2026-09-28: real next-gen successor to gemma2. |
| `deepseekcoderv2_16b` | `deepseek-coder-v2:16b` | 8.9GB | Added 2026-09-28: MoE code model, best "other" candidate found within the 16GB budget. |

Checked and **rejected** as not fitting the 16GB target or not a good fit: `qwen3-coder` (smallest tag is 30B/19GB), `codestral:22b` (13GB — too little headroom left for serving overhead), `duckdb-nsql` (tuned for DuckDB dialect, not SQLite — wrong fit for this pipeline's execution grading).

## Architecture

**Pipeline is three independent stages, glued only by files on disk — no shared in-memory state:**

1. **`scripts/prepare_dataset.py`** — extracts `data/spider_data.zip` (the Spider text-to-SQL benchmark's questions + real SQLite databases, re-hosted at HF dataset `HAL-9001/spider-databases` since the canonical `xlangai/spider` only ships question/SQL pairs, not the databases needed for execution grading). Builds a compact `CREATE TABLE`-style schema string per database from `tables.json`, tags each question with a complexity bucket (`simple`/`moderate`/`complex` — a local heuristic based on JOIN/GROUP BY/subquery/aggregate counts, **not** Spider's official hardness classifier), samples (currently targets the full dev split — see Commands), verifies the gold SQL actually executes, and writes the self-contained `data/eval_sample.json` (each entry carries its own schema text + sqlite path, so downstream steps need nothing else). Current state: **1032 questions, all 20 dev databases** (2 dropped — gold SQL didn't execute).

2. **`scripts/run_eval.py <model> <suffix> [batch_size] [--lever=<name>]`** — the evaluation loop. For each question: prompts the model via Ollama's HTTP API, extracts SQL from the response, executes both predicted and gold SQL against the question's real SQLite db (read-only), and grades by **execution accuracy** — order-insensitive multiset comparison of result rows (not string/AST comparison against gold SQL), so equivalent-but-differently-phrased SQL still counts correct. Writes one row per question incrementally (flushed after each) to `results/runs/<lever>/results_<suffix>.csv`, appending/resuming — see "Batching & resume" above.

   Most models go through `/api/chat` with a system+user message pair. **SQLCoder is a special case**: Ollama packages it with a bare passthrough template (`{{ .Prompt }}`, no chat roles), so sending it chat-formatted messages makes it echo the prompt back instead of answering. It's routed through `/api/generate` with Defog's documented raw completion template instead (see `SQLCODER_PROMPT_TEMPLATE` in `run_eval.py`). If adding another raw/completion-style model, check `ollama show <model> --modelfile` first — if `TEMPLATE` is a bare `{{ .Prompt }}`, it needs the same treatment.

3. **`scripts/aggregate.py [lever_name]`** — reads every `results/runs/<lever>/results_*.csv` present (via the `MODELS` dict mapping suffix → display name), computes overall/per-bucket/per-db accuracy, latency, and error rate, writes that lever's `summary.json`, and appends a row per model to the master `results/progress_log.csv`. Silently skips any model suffix with no results file yet under that lever, so it's safe to run mid-study.

There's no orchestrator script chaining steps 2 and 3 across all models — each `run_eval.py` invocation and each `aggregate.py` call are run manually per model/lever.

## Spider 2.0 (future track — not started)

See `spider2/README.md`. Deliberately kept separate from the pipeline above: Spider 2.0 is agentic (multi-turn tool use, not one-shot prompt→SQL), needs cloud DB access for most of it (only the DuckDB/DBT subset is offline-compatible), and top frontier models score ~10-17% on it — not a target to chase toward a specific accuracy number the way Spider 1.0 is. Pick this up only once Spider 1.0 lever-tuning stops moving the needle.

## Gotchas learned during this study

- **CSV row counts via `wc -l` are unreliable** for these result files — the `raw_response` field can contain embedded newlines inside a quoted CSV field, inflating the line count above the real record count. Always count real rows via `csv.DictReader`, not `wc -l`.
- Ollama's CLI progress bar (`ollama pull`) writes single-line `\r`-updated output; piping it through `| tail -N` buffers everything until the process exits, so live progress won't appear in a redirected/background log until completion. Redirect directly (`ollama pull x > log 2>&1 &`) if you need to tail live progress.
- This network has intermittently stalled large in-flight downloads after system sleep/resume; `ollama pull` resumes from partial blobs on retry, so just re-run the same `ollama pull` command if a download appears stuck.
- **`run_eval.py`'s own progress prints can look silent even when it's actively running**, if stdout is redirected to a log file rather than a terminal — Python fully buffers stdout when it's not a TTY, so `print()` lines sit in a buffer instead of hitting disk until it fills or the process exits. Don't trust an empty/stale-looking log file as a sign of a hang; check real progress via the results CSV's row count instead (`python3 -c "import csv; print(len(list(csv.DictReader(open('results/runs/spider_baseline/results_<suffix>.csv')))))"`).
- `sqlite3` CLI is not installed on this box by default (`which sqlite3` comes up empty) — use Python's `sqlite3` module for ad hoc queries, or `sudo apt install sqlite3` if you want the CLI (needs an interactive password prompt — can't be run non-interactively).
- Valentina Studio (GUI SQLite browser, installed 2026-09-28 at `/opt/VStudio/vstudio`) does **not** reliably accumulate a multi-database list when several instances are launched concurrently from the command line — they're separate OS processes sharing one settings file (`~/.config/ParadigmaSoft/VStudio/BookmarksAndRecents.conf`), and concurrent writes race/overwrite each other. Add databases one at a time through the GUI's own "+" button in a single running instance if you need the list to persist across restarts.
- `pkill`/similar process-killing commands in this environment sometimes report a nonstandard exit code (144) even when the kill actually succeeded — don't treat that exit code alone as failure; verify with `pgrep -af <name>` afterward.

## Changelog

Dated log of structural/behavioral changes to this project. Add an entry here whenever one of the sections above changes, don't just edit the section silently.

- **2026-10-09:** Added root and data READMEs documenting the agreed Git/data policy, dependencies, ignore rules, and intended post-clone setup. Spider sources will be downloaded separately; small fixed inputs and study evidence remain versioned. Added `.gitignore` and `requirements.txt`; a verified dataset downloader and path portability fixes remain pending. No scripts, datasets, or results changed.

- **2026-10-06:** Wired reviewed structural notes and question-grounding candidates into a separate direct-SQL Qwen 14B runner. It uses the full data-only schema, saves each result immediately, resumes by ID, and reports paired recovered/regressed IDs against the read-only baseline. The catalog remains structural v1 and has no business-owner approval or grounded-run score yet.
- **2026-10-06:** Reviewed the generated catalog against all 20 Spider dev schemas and SQLite rows. Removed an internal SQLite table and unverified row-grain assertions from the raw index; fixed grounding to retain parallel foreign-key alternatives and filter generic word/value collisions. Added `data/reviewed_semantics.md` with manually authored structural notes, including duplicated metadata keys, the flight airport whitespace mismatch, and observed undeclared joins.
- **2026-10-06:** Added source-grounded catalog files for all 20 Spider dev databases and a fast question-grounding preview. The catalog combines existing Spider metadata with bounded observed text values and declared join paths; it reads no dev questions or gold SQL. Retrieval produced candidate context for all 1,032 questions without Ollama. Direct-SQL evaluator prompts are unchanged; the JSON compiler experiment remains separate and is not part of the chosen local pipeline.
- **2026-10-06:** Clarified `ARCHITECTURE.md` and the study framing: Qwen is the current local foundation, while the competition compares complete local and deployed text-to-SQL pipelines using the same Spider IDs and grader. Lambda evaluation code exists; its full benchmark result remains planned.
- **2026-10-06:** Added the `json_compiler` Qwen 14B full Spider dev experiment: one JSON-mode Ollama response per question, a restricted parameterized SQLite compiler, resumable separate CSV, and an automatically updated paired comparison against the frozen SQL baseline. Local compiler tests and prompt dry run passed; live Ollama remains inaccessible from the Codex sandbox, so no new model score is claimed yet.

- **2026-10-06:** Clarified the per-client LoRA target as a tool-using SQL agent. Training requires both simple SQL building blocks and reviewed multi-step trajectories with SQL tool calls, observed results, and final answers. Spider question/SQL pairs alone do not provide those trajectories; simulated-client trajectories must be derived and checked. Evaluation must measure the full agent loop against an untuned agent and direct-SQL baseline.
- **2026-10-06:** Clarified that the target LoRA architecture is one adapter per client, selected by authenticated client ID. A shared Spider adapter is not the intended deployment design. Spider train databases may simulate clients for a training-method check, while real client adapters require that client's approved question/SQL pairs and held-out evaluation.
- **2026-10-06:** Added `--single-call` to the Qwen failed-ID retry runner after the first two-stage question took 201.6 seconds and still failed: its plan incorrectly required one `ship.name` to equal both requested ship names. The one-request variant skips the separate plan and explicitly handles two values in separate related rows; it has separate resumable output and has not yet been scored against Ollama.
- **2026-10-06:** Added per-ID and per-request progress logging with a 15-second Ollama heartbeat to the Qwen failed-ID retry runner. Ctrl+C now prints how many complete retry rows are saved and exits cleanly; rerunning resumes from those IDs. This followed a user interruption during the first, previously silent, planning request.
- **2026-10-06:** Added `scripts/retry_qwen_failures.py` to rerun only the 224 failed Qwen 14B Spider dev IDs with data-grounded values, a query plan, and one error-triggered SQL repair. It resumes by ID, preserves the original results, and reports exact recovery plus a separate column-permutation diagnostic. A dry run and local mocked repair check passed; live Ollama requests remain blocked by the Codex sandbox's localhost socket restriction.
- **2026-10-05:** Added `scripts/build_semantics_json.py` and generated `data/semantics_json/` for all 166 Spider schemas. The JSON shape includes entities, terms, metrics, query rules, assumptions, and example interpretations; only source-grounded facts and structural row-count metrics are populated. The JSON remains unwired from both runners.
- **2026-10-05:** Added `scripts/run_all_models.py` to resume the seven-model Spider dev run sequentially in 250-question batches under `results/runs/spider_baseline/`. It checks Ollama before writing results, pulls missing models, validates saved question IDs, and aggregates after all seven finish. Run with `python3 scripts/run_all_models.py` in an environment that can access local Ollama; the Codex sandbox blocks localhost sockets.
- **2026-10-05:** Documented five planned levers in `levers/MANIFEST.md` and individual writeups: a plain-schema control, question grounding, execution repair, query planning, and few-shot examples. Updated the current baseline description to match the actual Spider dev results and the safe data-only semantic layer. No new lever has been implemented or evaluated.
- **2026-10-05:** Reordered `scripts/run_all_models.py` so Qwen 2.5 Coder 14B runs first, then Qwen 2.5 Coder 7B, per the user's priority. The existing Gemma partial run is resumed afterward; completed Llama rows are skipped.
- **2026-10-05:** Added `insights/` and `scripts/analyze_qwen14.py` for a full Qwen 14B failure report. The sequential runner calls the analysis after Qwen has all 1,032 unique Spider dev IDs and before starting Qwen 7B. The report compares Qwen and Llama on identical questions, breaks out complexity and SQL constructs, and samples errors for manual review.
- **2026-10-07:** Recorded the completed question-grounded semantic catalog run for Qwen 14B: 788/1,032 (76.4%), compared with 808/1,032 (78.3%) baseline. Added a paired plain-English presentation variant that uses the same retrieved facts and evaluation settings; the English run is pending.
- **2026-10-05:** Qwen 14B's first 250-question batch saved one Ollama read timeout (ID 23) as an incorrect prediction, which blocked the sequential runner's integrity check. Removed that one row after a backup so it can be retried. `run_eval.py` now allows 300 seconds per request and aborts without recording a failed request as a wrong SQL answer; rerunning resumes at the unrecorded ID.
- **2026-10-05:** Added `scripts/watch_qwen14.py` so an already-running external Qwen 14B evaluation can trigger the insights report only after all 1,032 unique IDs arrive. The analyzer refuses partial data.
- **2026-10-05:** Added a separate `scripts/run_cloud_eval.py` and `cloud/README.md` for the teammate's Lambda model roster. It sends all 1,032 Spider dev questions with plain and data-only semantic schemas via curl, supports a configurable payload and response path, resumes by ID, grades locally, and writes only to `results/cloud/`. The endpoint contract is pending; no cloud requests have been sent.
- **2026-10-05:** Qwen 2.5 Coder 14B completed Spider dev at 808/1,032 (78.3%); manually reviewed its failures in `insights/qwen25coder_14b_review.md`. A separate column-permutation diagnostic found 49 locally equivalent outputs with reversed/rearranged columns among its recorded mismatches; the main score remains unchanged. Qwen 7B began next.
- **2026-10-05:** User paused Qwen 2.5 Coder 7B after a partial run. `run_all_models.py` now skips it on future starts, preserves its CSV, and skips full-roster aggregation while it is paused. An already-running external process still needs Ctrl+C in its terminal; editing the script does not interrupt that process.
- **2026-10-05:** Prioritized Gemma 3 12B as the next model. `run_all_models.py --only gemma3_12b` now runs only Gemma 3 in resumable batches, with a check for an active `run_eval.py` process before loading it. Qwen 7B remains paused and its partial CSV stays intact.
- **2026-10-05:** Gemma 3's first 19 answers took roughly 75 seconds each, versus Qwen 14B's roughly 13-second median on matching IDs; the earlier Gemma 2 partial run had a 49-second median. Paused both Gemma runs while preserving their CSVs, moved DeepSeek Coder V2 next, and added `--max-new N` with `--only` for a short resumable speed trial. The current host terminal run must be interrupted with Ctrl+C before trying another model; edits cannot stop its active child process.
- **2026-10-05:** DeepSeek Coder V2 completed 1,032 Spider dev questions at 711 correct (68.9%) and 4.0 seconds median. Documented the Qwen 14B latency distribution in `insights/qwen14_latency.md` and added `scripts/profile_qwen_latency.py` to collect Ollama's load/prompt/generation timings on the laptop without altering benchmark results.
- **2026-10-05:** Added a planned `sft_lora` lever and per-client adapter design. The Spider train split has 7,000 pairs across 140 databases, with no database overlap against the 20 dev databases. No adapter has been trained or connected to Ollama; client-specific SFT requires approved question/SQL pairs, not schema JSON alone.

- **2026-09-29:**
  - Reset the eval set from a 150-target/149-actual sample to the **full Spider dev split**: `SAMPLE_SIZE = 1034` in `prepare_dataset.py`, landing at **1032 questions across all 20 dev databases** (2 dropped on the gold-SQL-execution sanity check). The prior sample only covered 19/20 dbs (missing `real_estate_properties`, which has just 4 questions in dev — too small to survive stratified sampling at N=150).
  - **Deleted** the old 149-question `results/results_*.csv`, `results/summary.json`, `results/summary_report.csv`, `results/by_complexity/` — superseded, not comparable to the new N=1032 baseline.
  - Restructured results storage around **levers**: `results/runs/<lever>/results_<suffix>.csv` + `summary.json` per lever, plus a master `results/progress_log.csv` appended to by every `aggregate.py` run. Added `levers/MANIFEST.md` + per-lever `.md` writeups (hypothesis, implementation, results, accept/reject verdict) — see "Lever manifest" above.
  - `run_eval.py` rewritten for **batching + resume**: optional `batch_size` arg, always appends (never overwrites) `results_<suffix>.csv`, skips already-done question ids automatically, added `--lever=<name>` to route output under `results/runs/<lever>/`. Needed because a full 1032-question run against one model can take hours; batches (e.g. 250 at a time) let this be split across sessions without duplicate/lost data.
  - `aggregate.py` updated to take an optional `[lever_name]` arg (default `baseline`), read/write within that lever's folder, and append per-model rows to `results/progress_log.csv`.
  - Switched the CPU governor from `powersave` to `performance` (`sudo cpupower frequency-set -g performance`, run by the user) — measured **~45% faster inference** (19.2s/question -> 10.7s/question on `llama3.1:8b`). No code change, but materially changes ETA math for any future estimate.
  - **Merged the `semantic_layer` lever into `baseline` before either was run at full scale.** Original plan was plain-schema `baseline` vs. annotated-schema `semantic_layer` as two separate levers; given a full 1032×7 run takes ~22 hours even post-CPU-fix, running the plain-schema version first just to immediately supersede it wasn't worth the time. `run_eval.py` now has `load_schema(ex)`, which reads `data/semantic_layer/<db_id>.sql` unconditionally (falls back to plain `schema_text` only if a db's semantic file is missing). Consequence: **there is no same-scale plain-vs-semantic comparison anymore** — see `levers/baseline.md` and `levers/semantic_layer.md` for the full reasoning. Also generated the previously-missing `data/semantic_layer/real_estate_properties.sql` (the 20th db, not covered by the original 19-db draft).
  - Cleared the ~60 partial rows of plain-schema baseline results (`results/runs/baseline/results_llama31_8b.csv`) generated before the merge above — inconsistent with the redefined baseline, not worth keeping.
  - Baseline chain relaunched with the corrected (semantic-layer) schema source, batches of 250, all 7 models sequentially: `llama31_8b → gemma2_9b → qwen25coder_7b → sqlcoder_7b → qwen25coder_14b → gemma3_12b → deepseekcoderv2_16b`.
- **2026-09-28:**
  - Added 3 models to the roster, chosen against a **16GB RAM target (the eventual cloud deployment budget)**, not this dev box's ~24GB: `qwen2.5-coder:14b`, `gemma3:12b`, `deepseek-coder-v2:16b`. See "Model roster" above for what was checked and rejected.
  - Drafted the **semantic_layer** lever: `scripts/build_semantic_schema.py` generates `data/semantic_layer/<db_id>.sql` for all 19 (now 20, once regenerated) eval-sample databases. Code-derived annotations only (real sample values, auto-detected FK quirks) — no invented business documentation, since Spider ships none. Not yet wired into `run_eval.py`'s prompt.
  - Added `spider2/` as an explicitly-not-started scaffold for a future Spider 2.0 track — see its own README for why it's architecturally a different kind of eval (agentic, not single-shot) and isn't a simple dataset swap.
  - Installed Valentina Studio (GUI SQLite browser) for manual DB inspection — see Gotchas for its multi-instance settings-race quirk.
