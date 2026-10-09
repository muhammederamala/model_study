"""Run the frozen college_2 test set with an Ollama base or adapter model.

Examples:
  python3 lora_study/college_2/evaluate.py --phase baseline --dry-run
  python3 lora_study/college_2/evaluate.py --phase baseline --max-new 3
  python3 lora_study/college_2/evaluate.py --phase adapter --model <adapter-tag>
"""

import argparse
import csv
import hashlib
import json
import sys
import threading
import time
from pathlib import Path

import requests


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ground_question as grounding
from run_eval import SYSTEM_PROMPT, extract_sql, rows_match, run_sql


DB_ID = "college_2"
BASE_MODEL = "qwen2.5-coder:14b"
OLLAMA = "http://localhost:11434/api/chat"
FIELDS = ["id", "db_id", "complexity_bucket", "question", "gold_sql", "pred_sql",
          "grounding_context", "raw_response", "exec_error", "exec_match", "latency_sec",
          "prompt_eval_count", "eval_count"]

# Reuse the exact dev-study grounding algorithm, pointed at this study's
# isolated catalog and reviewed notes. This process never edits shared files.
grounding.CATALOG_DIR = HERE
grounding.REVIEWED = HERE / "reviewed_semantics.md"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prompt_for(example):
    catalog = json.loads((HERE / "catalog.json").read_text())
    result = grounding.ground(example["question"], catalog)
    context = grounding.format_context(result)
    prompt = (f"### Database Schema:\n{(HERE / 'schema.sql').read_text()}\n"
              f"### Additional Database Context:\n{context}\n\n"
              f"### Question:\n{example['question']}\n\n### SQL Query:")
    return prompt, context


def read_rows(path):
    if not path.exists():
        return {}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"unexpected output columns: {path}")
        rows = {}
        for row in reader:
            key = row["id"]
            if key in rows or key == "id":
                raise ValueError(f"duplicate or header ID {key} in {path}")
            rows[key] = row
    return rows


def run_id(model):
    return {"db_id": DB_ID, "model": model, "temperature": 0, "num_predict": 300,
            "test_sha256": sha256(HERE / "test.json"),
            "split_manifest_sha256": sha256(HERE / "split_manifest.json"),
            "schema_sha256": sha256(HERE / "schema.sql"),
            "catalog_sha256": sha256(HERE / "catalog.json"),
            "reviewed_notes_sha256": sha256(HERE / "reviewed_semantics.md"),
            "runner_sha256": sha256(Path(__file__)),
            "grounder_sha256": sha256(ROOT / "scripts/ground_question.py"),
            "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()}


def ask(model, example, prompt):
    payload = {"model": model, "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}],
        "stream": False, "options": {"temperature": 0, "num_predict": 300}}
    start = time.monotonic()
    done = threading.Event()

    def heartbeat():
        while not done.wait(15):
            print(f"  ID {example['id']}: waiting for Ollama ({int(time.monotonic()-start)}s)",
                  flush=True)

    watcher = threading.Thread(target=heartbeat, daemon=True)
    watcher.start()
    try:
        response = requests.post(OLLAMA, json=payload, timeout=(10, 600))
        response.raise_for_status()
        return response.json(), time.monotonic() - start
    finally:
        done.set()
        watcher.join(timeout=1)


def grade(example, response, elapsed, context):
    raw = response["message"]["content"]
    sql = extract_sql(raw)
    gold_rows, gold_error = run_sql(example["sqlite_path"], example["gold_sql"])
    if gold_error:
        raise RuntimeError(f"gold SQL failed for ID {example['id']}: {gold_error}")
    pred_rows, error = run_sql(example["sqlite_path"], sql) if sql else (None, "empty prediction")
    return {"id": example["id"], "db_id": example["db_id"],
            "complexity_bucket": example["complexity_bucket"],
            "question": example["question"], "gold_sql": example["gold_sql"],
            "pred_sql": sql, "grounding_context": context, "raw_response": raw,
            "exec_error": error or "", "exec_match": rows_match(gold_rows, pred_rows),
            "latency_sec": round(elapsed, 2),
            "prompt_eval_count": response.get("prompt_eval_count", ""),
            "eval_count": response.get("eval_count", "")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=("baseline", "adapter"))
    parser.add_argument("--model", help="Ollama model tag; baseline defaults to Qwen 14B")
    parser.add_argument("--max-new", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.max_new is not None and args.max_new < 1:
        parser.error("--max-new must be positive")
    model = args.model or (BASE_MODEL if args.phase == "baseline" else None)
    if not model:
        parser.error("--model is required for adapter phase")
    if args.phase == "adapter" and model == BASE_MODEL:
        parser.error("adapter model must have a different Ollama tag")
    examples = json.loads((HERE / "test.json").read_text())
    keys = {str(ex["id"]) for ex in examples}
    if len(keys) != len(examples):
        raise ValueError("duplicate test IDs")
    if args.dry_run:
        prompt, _ = prompt_for(examples[0])
        print(f"Model: {model}\nSystem:\n{SYSTEM_PROMPT}\n\n{prompt}")
        return
    folder = HERE / "runs" / args.phase
    output = folder / "results.csv"
    manifest_path = folder / "manifest.json"
    current = read_rows(output)
    if not set(current) <= keys:
        raise ValueError("output contains IDs outside this test split")
    identity = run_id(model)
    if manifest_path.exists():
        if json.loads(manifest_path.read_text()) != identity:
            raise ValueError("run inputs changed; refusing to mix results")
    elif current:
        raise ValueError("existing results have no manifest")
    remaining = [ex for ex in examples if str(ex["id"]) not in current]
    todo = remaining[:args.max_new] if args.max_new else remaining
    if not todo:
        print(f"{args.phase}: all {len(examples)} test IDs complete")
        return
    try:
        requests.get("http://localhost:11434/api/tags", timeout=5).raise_for_status()
    except requests.RequestException as error:
        raise SystemExit(f"Cannot reach local Ollama ({error}). No results were written.") from None
    folder.mkdir(parents=True, exist_ok=True)
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps(identity, indent=2) + "\n")
    print(f"{args.phase} {model}: {len(current)}/{len(examples)} saved; running {len(todo)}", flush=True)
    with output.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if output.stat().st_size == 0:
            writer.writeheader()
            handle.flush()
        try:
            for number, example in enumerate(todo, 1):
                print(f"[{number}/{len(todo)}] ID {example['id']}: {example['question']}", flush=True)
                prompt, context = prompt_for(example)
                response, elapsed = ask(model, example, prompt)
                row = grade(example, response, elapsed, context)
                writer.writerow(row)
                handle.flush()
                current[str(example["id"])] = {key: str(value) for key, value in row.items()}
                print(f"  ID {example['id']}: {'correct' if row['exec_match'] else 'wrong'} "
                      f"in {elapsed:.1f}s; {sum(x['exec_match']=='True' for x in current.values())}"
                      f"/{len(current)} correct", flush=True)
        except KeyboardInterrupt:
            print(f"Interrupted; {len(current)} rows saved. Rerun to resume.", file=sys.stderr)
            raise SystemExit(130)
    print(f"Saved {len(current)}/{len(examples)}: {output}")


if __name__ == "__main__":
    main()
