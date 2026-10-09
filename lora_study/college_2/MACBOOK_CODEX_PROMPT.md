# Task for MacBook Codex: train a `college_2` Qwen LoRA adapter

You have no prior context. I am running a text-to-SQL study on a Linux laptop. I want to train **one LoRA adapter for one database**, `college_2`, on this MacBook M4, then transfer the adapter to the Linux system and compare it with untuned Qwen on exactly the same held-out questions. Keep the adapter weights separate from the base model for the intended tenant-routing architecture. A merged model is only a fallback for a local compatibility test.

## Dataset and fixed study inputs

Use **Spider 1.0**, not Spider 2.0. Official dataset page: https://yale-lily.github.io/spider . Its current dataset link is https://drive.google.com/file/d/1403EGqzIDoHMdQF4c9Bkyl7dZLZ5Wt6J/view?usp=sharing . The relevant files in the archive are `train_spider.json`, `tables.json`, and `database/college_2/college_2.sqlite`. Filter `train_spider.json` for `db_id == "college_2"`: there should be **170 question–SQL pairs**, 11 tables, and a populated SQLite database. Do not use `geo` or `scholar`; their SQLite tables are empty in our downloaded bundle.

The Linux project has a prepared study bundle at `lora_study/college_2/`. Ask me to transfer that folder if it is not present on this Mac. It contains `train_sft.jsonl` (118 examples), `validation_sft.jsonl` (26), `test.json` (26), `schema.sql`, `catalog.json`, `reviewed_semantics.md`, `split_manifest.json`, and the scripts. **Treat that bundle as the source of truth for prompts and splits.** Do not silently create a new random split or a different schema prompt. The training conversations already include the full data-only schema and question-grounded context; they were generated without test answers. The adapter should learn to output a single SQLite query directly, not a JSON plan or multi-call agent trajectory.

For verification, the Spider source SHA-256 values in our bundle are:

- `train_spider.json`: `c43d0d72e59e1a9e1a60837da9bf70d5a6277226bdb7f634d544f380646f527a`
- `tables.json`: `61bb20aa401f03164e2d7f3b16509b7b5f79cc9c943ca7bd159046df1159e2ed`
- `college_2.sqlite`: `cb729920ad0b7f06d38a12f6f678307964acc7d3417af83d98c519c65c90d386`
- Prepared `train_sft.jsonl`: `eaa37e588a3bb95b640e5719f8dd68af4aa1e14298467085197362a0c6c2ed29`
- Prepared `validation_sft.jsonl`: `8fdd94ac3696a02445030ccf32baada68667d6f74d29d85aa3fcd2152845a830`

The split uses source-array positions as IDs. Held-out **test IDs** are `1338, 1339, 1346, 1347, 1352, 1353, 1382, 1383, 1386, 1387, 1422, 1423, 1424, 1425, 1428, 1429, 1430, 1431, 1436, 1437, 1442, 1443, 1454, 1455, 1482, 1483`. Validation IDs are `1324, 1325, 1358, 1359, 1368, 1369, 1388, 1389, 1394, 1395, 1400, 1401, 1408, 1409, 1438, 1439, 1440, 1441, 1446, 1447, 1458, 1459, 1468, 1469, 1484, 1485`. The remaining 118 `college_2` IDs are training data. The prepared split also groups normalized SQL patterns with literals masked, to keep close paraphrases together.

## Model and training requirements

The Linux baseline currently calls Ollama model `qwen2.5-coder:14b` with temperature 0, `num_predict=300`, the same system message and grounded user prompt present in the SFT conversations. A likely trainable source is https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct , but **verify its architecture, revision, tokenizer, and chat template against the Ollama model before training**. Record the exact Hugging Face commit or local model hash. Do not silently switch to 7B or another base if 14B does not fit. Inspect the Mac's unified memory, disk space, and available training framework first; tell me if this M4 cannot safely train the chosen 14B setup.

Implement a small LoRA/QLoRA SFT run on the 118 training conversations. Compute loss on assistant SQL tokens only; mask system/user text. Use the 26 validation examples for checkpoint selection and early stopping. Start with a short smoke test that checks tokenization, nonempty assistant labels, loss reduction, a generated SQL sample, and saved/reloaded adapter behavior before a full run. Keep the test IDs and test SQL completely out of training, prompt selection, and hyperparameter tuning. Do not upload model weights or data to any external service without my approval.

## Portability and deliverables

The target deployment design uses one shared Qwen base with a selectable adapter per tenant. A Mac MLX adapter file may need conversion before a Linux serving runtime can load it. **Verify a concrete, reversible export/load path before committing to long training.** Current Ollama does not directly import LoRA adapters; do not claim that copying a file into Ollama will work. Prefer a portable PEFT-compatible adapter or a verified GGUF adapter path if it preserves the exact base. Keep original adapter weights regardless of any merged export. If the current Linux Ollama setup cannot serve the adapter, identify an adapter-capable runtime and its Linux hardware requirements. Do not treat merging as equivalent to hot-swapping adapters.

Deliver: the training script/config, adapter weights, tokenizer/config references, a manifest with exact base revision and split hashes, validation metrics and example SQL, a tested reload/export procedure, and exact commands for transferring and loading the adapter on Linux. Explain any mismatch with the existing Ollama baseline and whether a same-base baseline must be rerun. The Linux study runner will later evaluate the untuned and tuned models on the same 26 `college_2` test IDs in separate result folders; do not modify the ongoing 1,032-question Spider dev evaluation.
