# College 2 per-database LoRA study

This folder is isolated from the 20-database Spider dev evaluation. `college_2` is the largest **populated** training database in the downloaded bundle: 170 question/SQL pairs and 11 tables. The previously suggested `geo` database has 564 pairs but **all seven SQLite tables are empty**; execution accuracy there would reward empty answers. `scholar` is empty too. `college_2` has 34,620 rows across its tables.

## Frozen inputs

`build.py` used only `train_spider.json`, `tables.json`, and the `college_2` SQLite file. It grouped normalized SQL patterns, masking literal values, before making a seed-42 split: **118 train / 26 validation / 26 test**. The test IDs and reference SQL stay in `test.json`; training exports never include them. `schema.sql` is the same data-only schema style used in the dev study. `catalog.json` uses the same catalog builder; its 11 entities and 20 declared relationship edges were reviewed against SQLite. Six Spider single-column primary-key labels proved non-unique and were removed from the prompt schema and catalog. The catalog includes observed one-character codes when quoted in a question; `reviewed_semantics.md` records composite joins and a partial time-slot code match. The baseline and adapter runner use the same question-grounding algorithm and the same prompt template. `split_manifest.json` records source and asset hashes. Do not rebuild after a run starts.

The test has only 26 examples, so this is a feasibility pilot rather than a precise accuracy estimate. Review ambiguous reference questions before interpreting a score. No question/SQL patterns are mined into the schema or catalog.

## Baseline, training data, and comparison

Run only one local Ollama evaluator at a time. While the 1,032-question dev run is active, prepare files and inspect prompts, but wait to start this model run.

```bash
python3 lora_study/college_2/evaluate.py --phase baseline --dry-run
python3 lora_study/college_2/evaluate.py --phase baseline --max-new 3
python3 lora_study/college_2/evaluate.py --phase baseline
python3 lora_study/college_2/prepare_sft.py
```

The default baseline model is `qwen2.5-coder:14b`. `prepare_sft.py` writes `train_sft.jsonl` and `validation_sft.jsonl` in chat-message format, with the same schema and grounding context used at inference. Train a LoRA adapter on the training conversations only; use validation for model selection. A training script and serving path depend on the chosen GPU and exact Qwen base revision and are not yet configured. Record those along with tokenizer, prompt format, adapter weights, and training settings. A Mac-trained MLX adapter is not directly usable as this Linux Ollama tag: current Ollama rejects direct LoRA adapter imports, so fuse and convert to an Ollama-supported full model first, or choose another verified serving path. MLX's built-in GGUF export does not support Qwen2, so test the chosen conversion path before training. Rebuild the untuned baseline from the same base revision and quantization for a strict model-weight comparison.

Once the tuned model is served as a distinct Ollama model tag, run it on the same held-out test IDs:

```bash
python3 lora_study/college_2/evaluate.py --phase adapter --model <adapter-tag> --dry-run
python3 lora_study/college_2/evaluate.py --phase adapter --model <adapter-tag>
python3 lora_study/college_2/compare.py
```

Each phase saves rows immediately under `runs/<phase>/` and resumes by ID. Manifests reject changed inputs or a changed model tag. `compare.py` reports paired correct counts, recovered IDs, and regressed IDs; it reports full accuracy only when both runs cover all 26 test questions. This direct-SQL pilot does not train multi-call agent trajectories.
