# Per-database LoRA studies

Each subfolder is one isolated database study with fixed train, validation, and test IDs. Keep its catalog, reviewed notes, prompt, model revision, and grader fixed between baseline and adapter runs. Do not mix these outputs with `results/runs/spider_baseline/` or the 20-database grounded evaluation.

Start with [college_2](college_2/README.md). Its populated SQLite database supports execution-based comparison; the larger `geo` and `scholar` training databases in this download have empty tables and are unsuitable for that comparison without new data.
