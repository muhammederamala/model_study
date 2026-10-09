# Text-to-SQL evaluation study

This project compares local Ollama and deployed cloud text-to-SQL pipelines on a fixed Spider 1.0 evaluation set: 1,032 questions across 20 development databases. See [ARCHITECTURE.md](ARCHITECTURE.md) for the pipeline and [CLAUDE.md](CLAUDE.md) for the detailed study workflow.

## Git and dataset policy

The full downloaded Spider dataset will **not be committed to Git**. After cloning, users download and extract it locally. Code, fixed evaluation questions, semantic schemas and catalogs, reviewed notes, small study results, and the fixed LoRA pilot splits belong in Git.

The current `data/` folder is about 2 GB and includes duplicate database copies. Several files are over 100 MiB, which [GitHub blocks in ordinary Git](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github). The chosen workflow is a separate dataset download rather than Git LFS. See [data/README.md](data/README.md) for paths and reproducibility requirements.

## Setup after cloning

**This workflow is not yet fully implemented.** The repository now includes `.gitignore` rules and `requirements.txt`. A dataset download script and portable paths are still needed before a clone in another location can run end to end: several scripts and saved evaluation records use `/home/lenovo/Documents/model_study`. The steps below describe the intended onboarding workflow and available commands.

1. Use Python 3.10 or newer and create a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python3 -m pip install requests
   ```

   `requirements.txt` declares `requests>=2.31,<3`, the only external runtime dependency imported by the current project scripts. This is a version range, not an exact dependency lock. `openpyxl` was used for manual spreadsheet exports and `huggingface_hub` for an ad hoc dataset download; neither is currently required by the scripts. SQLite and `unittest` are included in Python. LoRA training dependencies are not configured yet.

2. Download the exact Spider archive and extract it into `data/spider_data/`, following [data/README.md](data/README.md). A checksum-verifying setup script still needs to be added. Retain the existing evaluation IDs and split files; downloading source data is not a reason to regenerate them.

3. For local evaluation, install [Ollama](https://ollama.com), start its service, and pull the model:

   ```bash
   ollama pull qwen2.5-coder:7b
   ```

4. Once paths are portable and the databases are available, run a small smoke batch from the project root:

   ```bash
   python3 scripts/run_eval.py qwen2.5-coder:7b qwen25coder_7b 10 --dataset=dev --lever=clone_smoke
   ```

   This writes separate resumable outputs under `results/runs/clone_smoke/`. Run only one local evaluator at a time. Use the documented study lever when intentionally continuing a study run. The study targets a 16 GB inference budget; model downloads also require local disk space.

## Run the 1,032-question evaluation

The fixed Spider dev set in `data/eval_sample.json` contains 1,032 questions from all 20 development databases. Each model's run resumes by question ID: rerunning the same command skips saved questions and continues with missing IDs. Do not run two local evaluators at the same time; they compete for RAM and CPU.

To run one model through all 1,032 questions in batches of 250:

```bash
ollama pull qwen2.5-coder:14b
python3 scripts/run_eval.py qwen2.5-coder:14b qwen25coder_14b 250 --dataset=dev --lever=spider_baseline
```

Repeat the command until all questions are complete. Results append to `results/runs/spider_baseline/results_qwen25coder_14b.csv`. The 250 argument is the maximum new questions per invocation. Use a different suffix for each model, and do not change it while continuing a run.

The sequential roster helper runs its configured models in 250-question batches, pulling a model if it is not installed:

```bash
python3 scripts/run_all_models.py
```

It safely resumes saved question IDs, checks for an active evaluator, and runs one model at a time. The checked-in roster and selection options are described below. The current runner has some models paused and may skip final aggregation; inspect its output and confirm each result CSV has 1,032 unique IDs before reporting a complete comparison.

You can run a short probe for one supported model with:

```bash
python3 scripts/run_all_models.py --only deepseekcoderv2_16b --max-new 10
```

`--only` takes the model's result suffix, not its Ollama name. It runs only that model; `--max-new` limits the number of new answers and is useful for checking setup, latency, and prompt behavior before a full run. The helper rejects models marked paused in its source. To choose another supported model, edit the `MODELS` roster in `scripts/run_all_models.py`; also add its result suffix and display name to `MODELS` in `scripts/aggregate.py` before expecting aggregation to include it. Pull the selected Ollama tag with `ollama pull <model>` or let the helper pull it.

The current roster is Qwen 2.5 Coder 14B, Qwen 2.5 Coder 7B, Gemma 3 12B, DeepSeek Coder V2 16B, Gemma 2 9B, Llama 3.1 8B, and SQLCoder 7B. The helper currently marks Qwen 7B, Gemma 3 12B, and Gemma 2 9B as paused, preserving their partial files. Model weights are downloaded separately by Ollama and can take multiple gigabytes each. For a controlled comparison, choose the models before starting, use the same fixed dev questions and lever, and record the exact Ollama tags.

After all selected result files are complete, aggregate a lever's results:

```bash
python3 scripts/aggregate.py spider_baseline
```

This writes `results/runs/spider_baseline/summary.json` and appends rows to `results/progress_log.csv`. Aggregation uses the configured roster in `scripts/aggregate.py`; it may include partial CSVs, so check coverage before treating a score as final. See [levers/MANIFEST.md](levers/MANIFEST.md) and the relevant lever note when interpreting results. The local grader checks whether predicted SQL returns the same result rows as reference SQL; it does not compare SQL strings.

Run the existing unit tests with Python's built-in test runner:

```bash
python3 -m unittest discover -s tests -v
```

These tests check the JSON-to-SQL compiler and question-grounding behavior. They are not the 1,032-question model evaluation; that evaluation calls Ollama and takes substantially longer.

For cloud evaluation, install `curl` and configure the endpoint, authentication, and response contract described in [cloud/README.md](cloud/README.md). Preview the first request without sending it, then run all remaining questions by omitting `--batch-size`:

```bash
python3 scripts/run_cloud_eval.py --run team_v1 --label cloud_qwen14 --dry-run
python3 scripts/run_cloud_eval.py --endpoint 'https://YOUR-ENDPOINT' --run team_v1 --label cloud_qwen14 --model qwen14 --response-path sql
```

Cloud grading still needs the local Spider databases. Keep credentials outside this project.

## Recommended ignore rules

The root `.gitignore` applies these rules:

```gitignore
# Python environments, caches, and build outputs
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
build/
dist/

# Secrets and local configuration
.env
.env.*
!.env.example
.aws/
*.pem
*.key

# Logs and OS metadata
*.log
*.pid
.DS_Store
__MACOSX/

# Downloaded Spider sources and caches
/data/spider_data.zip
/data/spider_data/
/data/.cache/
/data/__MACOSX/

# Machine-local dependency bootstrap
/tools/get-pip.py

# Future model and training artifacts
checkpoints/
adapters/
*.safetensors
*.gguf
```

Do not ignore all of `data/` or `results/`: the small fixed inputs and study evidence should remain versioned. Review any future model artifacts before adding them to Git.

## Remaining clone-readiness work

- Add a dataset download/extraction command that verifies the exact archive checksum.
- Replace machine-specific script roots with paths derived from `__file__`.
- Store project-relative SQLite paths in evaluation and pilot records and resolve them at runtime, preserving question IDs and splits. Update any affected manifests deliberately.
- Verify setup and a small evaluation from a different checkout location.
- Add a project license and dataset attribution before distribution.

The downloader and portable paths remain the main blockers to a working clone-and-run setup.
