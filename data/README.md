# Data storage and setup

The downloaded Spider 1.0 archive and extracted source databases are local setup inputs, **not Git-tracked files**. After cloning the project, download them separately. Keep fixed evaluation questions, schema assets, catalogs, and reviewed notes in Git so all users evaluate the same questions with the same context.

## Expected local layout

```text
data/
  spider_data.zip                         # downloaded archive; ignored
  spider_data/                           # extracted sources; ignored
    dev.json
    train_spider.json
    tables.json
    database/<db_id>/<db_id>.sqlite
  eval_sample.json                       # fixed 1,032-question dev evaluation
  invented_eval.json                     # fixed 500-question separate evaluation
  semantic_layer_dataonly/               # database-derived dev prompt context
  semantic_layer/                        # includes dev-answer-derived patterns
  semantic_catalog/                      # source-grounded retrieval assets
  semantics_json/                        # standalone generated schema facts
  reviewed_semantics.md                  # reviewed structural notes
```

The development evaluation requires all 20 databases referenced by `eval_sample.json`. The `college_2` LoRA pilot also requires `train_spider.json`, `tables.json`, and `database/college_2/college_2.sqlite`. Source archives may include extra files or duplicate directories; preserve the `database/` paths expected by this project. Download caches and `__MACOSX/` metadata are ignored.

## Download and reproducibility

The current bundle was downloaded from the Hugging Face dataset `HAL-9001/spider-databases` and saved as `data/spider_data.zip`. A future setup script must record the exact source revision and archive SHA-256, verify the download, and extract it to the expected layout. That script and a pinned archive manifest have not been added yet; there is no working one-command dataset setup at present.

Do not substitute another Spider bundle without checking compatibility. Execution results depend on the actual SQLite contents, and the pilot's `lora_study/college_2/split_manifest.json` records source and asset hashes.

`scripts/prepare_dataset.py` extracts the existing archive if needed and **rebuilds** `eval_sample.json`; it does not download the dataset. Run it only when intentionally changing the evaluation set. Normal clone setup should download/extract the source databases and reuse the fixed evaluation files. Likewise, retain the existing LoRA train/validation/test splits.

## Current portability limitation

The saved `sqlite_path` fields in `eval_sample.json`, `invented_eval.json`, and the `college_2` pilot records currently contain absolute paths under `/home/lenovo/Documents/model_study`. Some scripts also hardcode that project root. Before clone setup can work elsewhere, convert these paths to project-relative values and resolve them at runtime without changing question IDs, SQL, or split membership. Review manifest changes explicitly rather than rebuilding the study to fix paths.

See [the root README](../README.md) for dependencies, proposed ignore rules, and the remaining implementation work.
