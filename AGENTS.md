# Repository Guidelines

## Project Structure & Module Organization

This is a Python text-to-SQL evaluation study. `scripts/` contains dataset preparation, local Ollama evaluation, cloud evaluation, and aggregation tools. `data/` holds Spider questions, SQLite databases, evaluation sets, and generated semantic schemas. Local outputs go to `results/runs/<lever>/`; cloud outputs go to `results/cloud/<run>/`. `levers/` records hypotheses and verdicts, `insights/` holds analysis, and `spider2/` documents a future track. Read `CLAUDE.md` for the current study workflow and `cloud/README.md` for the endpoint contract.

## Development and Evaluation Commands

See `README.md` for clone-readiness status and `data/README.md` for dataset setup. The agreed workflow downloads Spider after cloning; exclude `data/spider_data.zip`, `data/spider_data/`, download caches, and OS metadata from Git. Keep small fixed evaluation inputs, semantic assets, reviewed notes, pilot splits, and study results versioned. Do not regenerate evaluation sets merely to set up a clone. Requirements, ignore rules, a checksum-verifying download script, and portable script/record paths are still pending; documentation alone does not implement them.

- `python3 -m pip install --user requests` installs the dependency used by local evaluation scripts.
- `python3 scripts/prepare_dataset.py` rebuilds `data/eval_sample.json`; run it only when intentionally changing the evaluation set.
- `python3 scripts/run_eval.py qwen2.5-coder:7b qwen25coder_7b 250 --dataset=dev --lever=spider_baseline` evaluates a resumable batch. Supply both flags explicitly; defaults target another dataset and output folder. Pull the model with `ollama pull <model>` first, and run only one local evaluator at a time.
- `python3 scripts/aggregate.py spider_baseline` updates that lever's summary and appends to `results/progress_log.csv`.
- `python3 scripts/run_cloud_eval.py --run team_v1 --label cloud_qwen14 --dry-run` previews a cloud request without sending it.

## Coding Style & Naming Conventions

Follow the existing Python style: four-space indentation, `snake_case` for modules and functions, `UPPER_CASE` for constants, and `pathlib.Path` for paths. Keep scripts focused on one pipeline step. Name per-model result files `results_<suffix>.csv` and lever notes `levers/<name>.md`. No formatter or linter configuration is present; keep changes consistent with nearby code.

## Testing Guidelines

There is no automated test suite or stated coverage target. For script changes, run `python3 -m py_compile scripts/<script>.py`, then use a small evaluation batch or the cloud `--dry-run` as appropriate. Check output IDs, row counts, and summaries before accepting a result; avoid rebuilding datasets or appending to the progress log merely to test code.

## Changes and Review

This directory has no usable Git history, so no commit-message convention can be inferred. If contributing through Git, use a short imperative subject and explain the dataset, model, or lever affected. In a pull request, include the command run, result location, accuracy or behavior change, and any comparison limits. Update `CLAUDE.md` for workflow changes and `levers/MANIFEST.md` plus the relevant lever note when an evaluation completes. Keep endpoint credentials outside this project.
