"""Export train/validation conversations; never export test answers for training."""

import json
from pathlib import Path

from evaluate import HERE, SYSTEM_PROMPT, prompt_for


def main():
    for part in ("train", "validation"):
        source = HERE / f"{part}.json"
        output = HERE / f"{part}_sft.jsonl"
        if output.exists():
            raise SystemExit(f"refusing to overwrite {output}")
        examples = json.loads(source.read_text())
        with output.open("w") as handle:
            for example in examples:
                prompt, _ = prompt_for(example)
                record = {"id": example["id"], "db_id": example["db_id"],
                          "messages": [
                              {"role": "system", "content": SYSTEM_PROMPT},
                              {"role": "user", "content": prompt},
                              {"role": "assistant", "content": example["gold_sql"]}]}
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"{part}: {len(examples)} conversations -> {output}")


if __name__ == "__main__":
    main()
