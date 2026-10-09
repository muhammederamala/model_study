"""Run the full Spider dev set with Qwen JSON plans and a SQLite compiler.

The original SQL baseline is read only. Resume with the same command; use
--max-new N for a pilot and --dry-run to inspect a prompt without Ollama.
"""

import argparse
import csv
import hashlib
import json
import sqlite3
import sys
import threading
import time
from pathlib import Path

import requests

from json_sql_compiler import JsonSqlCompiler, PlanError
from run_eval import load_schema, rows_match, run_sql


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/eval_sample.json"
SCHEMAS = ROOT / "data/semantic_layer_dataonly"
BASELINE = ROOT / "results/runs/spider_baseline/results_qwen25coder_14b.csv"
OUT_DIR = ROOT / "results/runs/json_compiler"
OUT_CSV = OUT_DIR / "results_qwen25coder_14b.csv"
MANIFEST = OUT_DIR / "run_manifest.json"
COMPARISON = OUT_DIR / "comparison_qwen25coder_14b.json"
MODEL = "qwen2.5-coder:14b"
OLLAMA = "http://localhost:11434/api/chat"
FIELDS = ["id", "db_id", "complexity_bucket", "question", "gold_sql", "pred_sql",
          "plan_json", "raw_response", "params_json", "compile_error", "exec_error",
          "exec_match", "latency_sec", "eval_duration_ns", "prompt_eval_count", "eval_count"]

SYSTEM = """You translate a question and SQLite schema into one JSON query plan. Return ONLY a JSON object, with no SQL or prose. Use only schema tables and columns. A plan has {"select":[expression,...],"from":{"table":"table","as":"alias"},"joins":[{"table":"table","as":"alias","kind":"inner|left|cross","on":expression}],"where":expression,"group_by":[expression,...],"having":expression,"order_by":[{"expr":expression,"direction":"asc|desc"}],"limit":integer,"distinct":true}. Optional keys can be omitted. Expressions are {"col":"alias.column"}, {"literal":value}, {"star":true}, {"func":"count|sum|avg|min|max|abs|round|lower|upper|length|coalesce","args":[expression,...],"distinct":true}, or {"op":"eq|ne|gt|gte|lt|lte|like|not_like|and|or|not|in|not_in|between|is_null|is_not_null|exists|add|sub|mul|div","args":[expression,...]}. For IN, use {"values":[value,...]} or {"subquery":query} as the right argument. Subqueries use {"subquery":query}. An extreme-value scalar can use {"argmax":{"table":"table","by":"column","value":"column"}}. For set operations use {"set_op":"union|union_all|intersect|except","queries":[query,query]}. Example for a hypothetical products(id, price) table and 'How many products cost more than 10?': {"select":[{"func":"count","args":[{"star":true}]}],"from":{"table":"products"},"where":{"op":"gt","args":[{"col":"price"},{"literal":10}]}}. Think through joins and aggregation, then output the plan."""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(examples):
    schema_hash = hashlib.sha256()
    for db_id in sorted({ex["db_id"] for ex in examples}):
        schema_hash.update(db_id.encode())
        schema_hash.update((SCHEMAS / f"{db_id}.sql").read_bytes())
    return {"model": MODEL, "dataset_sha256": digest(DATASET),
            "baseline_sha256": digest(BASELINE), "schema_sha256": schema_hash.hexdigest(),
            "compiler_sha256": digest(ROOT / "scripts/json_sql_compiler.py"),
            "prompt_sha256": hashlib.sha256(SYSTEM.encode()).hexdigest(),
            "num_predict": 1100, "temperature": 0, "format": "json"}


def read_rows(path):
    if not path.exists():
        return {}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if path == OUT_CSV and reader.fieldnames != FIELDS:
            raise ValueError(f"output columns differ from current runner: {path}")
        rows = {}
        for row in reader:
            key = str(row["id"])
            if key in rows:
                raise ValueError(f"duplicate ID {key} in {path}")
            rows[key] = row
        return rows


def report(baseline, current, examples):
    by_id = {str(ex["id"]): ex for ex in examples}
    wins = [int(key) for key, row in current.items()
            if row["exec_match"] == "True" and baseline[key]["exec_match"] != "True"]
    losses = [int(key) for key, row in current.items()
              if row["exec_match"] != "True" and baseline[key]["exec_match"] == "True"]
    buckets = {}
    for bucket in sorted({ex["complexity_bucket"] for ex in examples}):
        ids = [key for key in current if by_id[key]["complexity_bucket"] == bucket]
        buckets[bucket] = {"evaluated": len(ids),
                           "json_correct": sum(current[key]["exec_match"] == "True" for key in ids),
                           "baseline_correct_on_same_ids": sum(baseline[key]["exec_match"] == "True" for key in ids)}
    result = {"evaluated": len(current), "total": len(examples),
              "json_correct": sum(row["exec_match"] == "True" for row in current.values()),
              "baseline_correct_on_same_ids": sum(baseline[key]["exec_match"] == "True" for key in current),
              "recovered_ids": wins, "regressed_ids": losses,
              "compile_failures": sum(bool(row["compile_error"]) for row in current.values()),
              "sql_execution_failures": sum(bool(row["exec_error"]) for row in current.values()),
              "by_complexity": buckets}
    if len(current) == len(examples):
        result["json_accuracy"] = result["json_correct"] / len(examples)
        result["baseline_accuracy"] = result["baseline_correct_on_same_ids"] / len(examples)
    COMPARISON.write_text(json.dumps(result, indent=2) + "\n")
    return result


def ask(ex):
    payload = {"model": MODEL, "messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"### Database Schema:\n{load_schema(ex, SCHEMAS)}\n\n### Question:\n{ex['question']}\n\n### JSON Query Plan:"}],
        "format": "json", "stream": False,
        "options": {"temperature": 0, "num_predict": 1100}}
    started = time.monotonic()
    finished = threading.Event()

    def heartbeat():
        while not finished.wait(15):
            print(f"  ID {ex['id']}: waiting for Ollama ({int(time.monotonic() - started)}s)", flush=True)

    watcher = threading.Thread(target=heartbeat, daemon=True)
    watcher.start()
    try:
        response = requests.post(OLLAMA, json=payload, timeout=(10, 600))
        response.raise_for_status()
        return response.json(), time.monotonic() - started
    finally:
        finished.set()
        watcher.join(timeout=1)


def grade(ex, response, elapsed):
    raw = response["message"]["content"]
    plan_text = ""
    sql = ""
    params = ()
    compile_error = ""
    exec_error = ""
    pred_rows = None
    try:
        plan = json.loads(raw)
        plan_text = json.dumps(plan, ensure_ascii=False, separators=(",", ":"))
        sql, params = JsonSqlCompiler(ex["sqlite_path"]).compile(plan)
        with sqlite3.connect(f"file:{ex['sqlite_path']}?mode=ro", uri=True) as connection:
            connection.execute("PRAGMA query_only = 1")
            pred_rows = connection.execute(sql, params).fetchall()
    except (ValueError, TypeError, KeyError, sqlite3.Error) as exc:
        if sql:
            exec_error = str(exc)
        else:
            compile_error = f"{type(exc).__name__}: {exc}"
    gold_rows, gold_error = run_sql(ex["sqlite_path"], ex["gold_sql"])
    if gold_error:
        raise RuntimeError(f"gold SQL failed for ID {ex['id']}: {gold_error}")
    return {"id": ex["id"], "db_id": ex["db_id"],
            "complexity_bucket": ex["complexity_bucket"], "question": ex["question"],
            "gold_sql": ex["gold_sql"], "pred_sql": sql, "plan_json": plan_text,
            "raw_response": raw, "params_json": json.dumps(params),
            "compile_error": compile_error, "exec_error": exec_error,
            "exec_match": rows_match(gold_rows, pred_rows), "latency_sec": round(elapsed, 2),
            "eval_duration_ns": response.get("eval_duration", ""),
            "prompt_eval_count": response.get("prompt_eval_count", ""),
            "eval_count": response.get("eval_count", "")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-new", type=int, help="maximum new IDs this invocation")
    parser.add_argument("--dry-run", action="store_true")
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
        raise ValueError("baseline must contain exactly the full dataset IDs")
    if args.dry_run:
        ex = examples[0]
        print(f"Model: {MODEL}\nOutput: {OUT_CSV}\nFirst ID: {ex['id']}\n")
        print(SYSTEM + "\n\n" + load_schema(ex, SCHEMAS) + "\n\n" + ex["question"])
        return
    run_id = identity(examples)
    existing = read_rows(OUT_CSV)
    if not set(existing) <= keys:
        raise ValueError("output contains IDs outside the current dataset")
    if MANIFEST.exists():
        if json.loads(MANIFEST.read_text()) != run_id:
            raise ValueError("run configuration changed; refusing to mix results")
    elif existing:
        raise ValueError("existing CSV has no run manifest; refusing to append")
    todo = [ex for ex in examples if str(ex["id"]) not in existing]
    if args.max_new:
        todo = todo[:args.max_new]
    if not todo:
        print(f"All {len(examples)} IDs complete. Comparison: {COMPARISON}")
        return
    # Preflight before creating files, so a blocked socket never creates a partial run.
    try:
        requests.get("http://localhost:11434/api/tags", timeout=5).raise_for_status()
    except requests.RequestException as exc:
        raise SystemExit(
            f"Cannot reach local Ollama at localhost:11434 ({exc}). "
            "Run this command in a host terminal with Ollama available. "
            "No results were written."
        ) from None
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not MANIFEST.exists():
        MANIFEST.write_text(json.dumps(run_id, indent=2) + "\n")
    print(f"Qwen 14B JSON compiler: {len(existing)}/{len(examples)} saved; running {len(todo)} IDs. One Ollama response per ID.", flush=True)
    with OUT_CSV.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if not existing:
            writer.writeheader()
            handle.flush()
        try:
            for i, ex in enumerate(todo, 1):
                print(f"[{i}/{len(todo)}] ID {ex['id']} ({ex['db_id']}): {ex['question']}", flush=True)
                response, elapsed = ask(ex)
                row = grade(ex, response, elapsed)
                writer.writerow(row)
                handle.flush()
                existing[str(ex["id"])] = {key: str(value) for key, value in row.items()}
                summary = report(baseline, existing, examples)
                print(f"  ID {ex['id']}: {'correct' if row['exec_match'] else 'wrong'} in {elapsed:.1f}s; "
                      f"paired {summary['json_correct']}/{len(existing)} vs baseline "
                      f"{summary['baseline_correct_on_same_ids']}/{len(existing)}", flush=True)
        except KeyboardInterrupt:
            print(f"Interrupted. {len(existing)} completed IDs are saved; rerun to resume.", file=sys.stderr)
            raise SystemExit(130)
    summary = report(baseline, existing, examples)
    print(f"Saved {len(existing)}/{len(examples)} IDs to {OUT_CSV}; comparison: {COMPARISON}")
    if len(existing) == len(examples):
        print(f"Full-set accuracy: JSON {summary['json_correct']}/{len(examples)}; "
              f"baseline {summary['baseline_correct_on_same_ids']}/{len(examples)}")


if __name__ == "__main__":
    main()
