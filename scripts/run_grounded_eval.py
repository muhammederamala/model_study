"""Evaluate direct-SQL Qwen 14B with reviewed semantics and question grounding.

Writes only to results/runs/question_grounding/. The frozen direct-SQL baseline
is read for paired comparison. Resume with the same command after interruption.
Use --dry-run to inspect a prompt without calling Ollama.
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

from ground_question import CATALOG_DIR, REVIEWED, format_context, ground, load_catalog
from run_eval import SYSTEM_PROMPT, extract_sql, load_schema, rows_match, run_sql


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/eval_sample.json"
SCHEMAS = ROOT / "data/semantic_layer_dataonly"
BASELINE = ROOT / "results/runs/spider_baseline/results_qwen25coder_14b.csv"
OUT_DIR = ROOT / "results/runs/question_grounding"
OUT_CSV = OUT_DIR / "results_qwen25coder_14b.csv"
MANIFEST = OUT_DIR / "run_manifest.json"
COMPARISON = OUT_DIR / "comparison_qwen25coder_14b.json"
MODEL = "qwen2.5-coder:14b"
OLLAMA = "http://localhost:11434/api/chat"
FIELDS = ["id", "db_id", "complexity_bucket", "question", "gold_sql", "pred_sql",
          "grounding_context", "raw_response", "exec_error", "exec_match", "latency_sec",
          "prompt_eval_count", "eval_count"]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_folder(folder, ids):
    digest = hashlib.sha256()
    for db_id in sorted(ids):
        path = folder / f"{db_id}.{'sql' if folder == SCHEMAS else 'json'}"
        digest.update(db_id.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def identity(examples):
    ids = {ex["db_id"] for ex in examples}
    return {"model": MODEL, "temperature": 0, "num_predict": 300,
            "dataset_sha256": sha256(DATASET), "baseline_sha256": sha256(BASELINE),
            "schema_sha256": hash_folder(SCHEMAS, ids),
            "catalog_sha256": hash_folder(CATALOG_DIR, ids),
            "reviewed_notes_sha256": sha256(REVIEWED),
            "runner_sha256": sha256(Path(__file__)),
            "grounder_sha256": sha256(ROOT / "scripts/ground_question.py"),
            "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()}


def read_rows(path):
    if not path.exists():
        return {}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if path == OUT_CSV and reader.fieldnames != FIELDS:
            raise ValueError(f"unexpected output columns: {path}")
        rows = {}
        for row in reader:
            key = row["id"]
            if key in rows:
                raise ValueError(f"duplicate ID {key} in {path}")
            rows[key] = row
    return rows


def prompt_for(example):
    context = format_context(ground(example["question"], load_catalog(example["db_id"])))
    prompt = (f"### Database Schema:\n{load_schema(example, SCHEMAS)}\n\n"
              f"### Additional Database Context:\n{context}\n\n"
              f"### Question:\n{example['question']}\n\n### SQL Query:")
    return prompt, context


def ask(example, prompt):
    payload = {"model": MODEL, "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}],
        "stream": False, "options": {"temperature": 0, "num_predict": 300}}
    start = time.monotonic()
    done = threading.Event()

    def heartbeat():
        while not done.wait(15):
            print(f"  ID {example['id']}: waiting for Ollama ({int(time.monotonic() - start)}s)",
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
    pred_rows, pred_error = run_sql(example["sqlite_path"], sql) if sql else (None, "empty prediction")
    return {"id": example["id"], "db_id": example["db_id"],
            "complexity_bucket": example["complexity_bucket"],
            "question": example["question"], "gold_sql": example["gold_sql"],
            "pred_sql": sql, "grounding_context": context, "raw_response": raw,
            "exec_error": pred_error or "", "exec_match": rows_match(gold_rows, pred_rows),
            "latency_sec": round(elapsed, 2),
            "prompt_eval_count": response.get("prompt_eval_count", ""),
            "eval_count": response.get("eval_count", "")}


def report(baseline, current, examples):
    buckets = {}
    by_id = {str(ex["id"]): ex for ex in examples}
    for bucket in sorted({ex["complexity_bucket"] for ex in examples}):
        keys = [key for key in current if by_id[key]["complexity_bucket"] == bucket]
        buckets[bucket] = {"evaluated": len(keys),
                           "grounded_correct": sum(current[key]["exec_match"] == "True" for key in keys),
                           "baseline_correct_on_same_ids": sum(baseline[key]["exec_match"] == "True" for key in keys)}
    summary = {"evaluated": len(current), "total": len(examples),
               "grounded_correct": sum(row["exec_match"] == "True" for row in current.values()),
               "baseline_correct_on_same_ids": sum(baseline[key]["exec_match"] == "True" for key in current),
               "recovered_ids": [int(key) for key, row in current.items()
                                 if row["exec_match"] == "True" and baseline[key]["exec_match"] != "True"],
               "regressed_ids": [int(key) for key, row in current.items()
                                 if row["exec_match"] != "True" and baseline[key]["exec_match"] == "True"],
               "sql_errors": sum(bool(row["exec_error"]) for row in current.values()),
               "by_complexity": buckets}
    if len(current) == len(examples):
        summary["grounded_accuracy"] = summary["grounded_correct"] / len(examples)
        summary["baseline_accuracy"] = summary["baseline_correct_on_same_ids"] / len(examples)
    COMPARISON.write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-new", type=int, help="maximum new IDs to run")
    parser.add_argument("--dry-run", action="store_true", help="show one prompt without Ollama")
    args = parser.parse_args()
    if args.max_new is not None and args.max_new < 1:
        parser.error("--max-new must be positive")
    examples = json.loads(DATASET.read_text())
    examples.sort(key=lambda ex: (ex["db_id"], ex["id"]))
    keys = {str(ex["id"]) for ex in examples}
    if len(keys) != len(examples):
        raise ValueError("dataset has duplicate IDs")
    baseline = read_rows(BASELINE)
    if set(baseline) != keys:
        raise ValueError("baseline must contain exactly the dataset IDs")
    if args.dry_run:
        prompt, _ = prompt_for(examples[0])
        print(f"Model: {MODEL}\nOutput: {OUT_CSV}\nSystem:\n{SYSTEM_PROMPT}\n\n{prompt}")
        return
    run_id = identity(examples)
    current = read_rows(OUT_CSV)
    if not set(current) <= keys:
        raise ValueError("output contains IDs outside this dataset")
    if MANIFEST.exists():
        if json.loads(MANIFEST.read_text()) != run_id:
            raise ValueError("run inputs changed; refusing to mix results")
    elif current:
        raise ValueError("existing results have no manifest; refusing to append")
    remaining = [ex for ex in examples if str(ex["id"]) not in current]
    todo = remaining[:args.max_new] if args.max_new else remaining
    if not todo:
        print(f"All {len(examples)} IDs complete. Comparison: {COMPARISON}")
        return
    try:
        requests.get("http://localhost:11434/api/tags", timeout=5).raise_for_status()
    except requests.RequestException as error:
        raise SystemExit(f"Cannot reach local Ollama ({error}). No results were written.") from None
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not MANIFEST.exists():
        MANIFEST.write_text(json.dumps(run_id, indent=2) + "\n")
    print(f"Grounded Qwen 14B: {len(current)}/{len(examples)} saved; running {len(todo)} IDs.", flush=True)
    with OUT_CSV.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        # An interrupted run can leave a header-only CSV. Do not append a
        # second header when there are no completed rows yet.
        if OUT_CSV.stat().st_size == 0:
            writer.writeheader()
            handle.flush()
        try:
            for number, example in enumerate(todo, 1):
                print(f"[{number}/{len(todo)}] ID {example['id']} ({example['db_id']}): "
                      f"{example['question']}", flush=True)
                prompt, context = prompt_for(example)
                response, elapsed = ask(example, prompt)
                row = grade(example, response, elapsed, context)
                writer.writerow(row)
                handle.flush()
                current[str(example["id"])] = {key: str(value) for key, value in row.items()}
                summary = report(baseline, current, examples)
                print(f"  ID {example['id']}: {'correct' if row['exec_match'] else 'wrong'} "
                      f"in {elapsed:.1f}s; paired {summary['grounded_correct']}/{len(current)} "
                      f"vs baseline {summary['baseline_correct_on_same_ids']}/{len(current)}", flush=True)
        except KeyboardInterrupt:
            print(f"Interrupted; {len(current)} rows saved. Rerun to resume.", file=sys.stderr)
            raise SystemExit(130)
    print(f"Saved {len(current)}/{len(examples)} rows. Comparison: {COMPARISON}")


if __name__ == "__main__":
    main()
