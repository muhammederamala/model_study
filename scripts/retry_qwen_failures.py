"""Retry only failed Qwen 14B Spider dev IDs with grounding, planning, and SQL repair.

Usage: python3 scripts/retry_qwen_failures.py [--single-call] [--max-new N] [--dry-run]
The original baseline CSV is read-only. Repeated runs resume by question ID.
"""

import argparse
import csv
import json
import re
import sqlite3
import threading
import time
from collections import Counter
from itertools import permutations
from pathlib import Path

import requests

from run_eval import load_schema, normalize_cell, rows_match, run_sql


ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "data/eval_sample.json"
BASELINE = ROOT / "results/runs/spider_baseline/results_qwen25coder_14b.csv"
OUTPUT = ROOT / "results/retries/qwen25coder_14b_failed.csv"
SINGLE_OUTPUT = ROOT / "results/retries/qwen25coder_14b_failed_single_call.csv"
LAYER = ROOT / "data/semantic_layer_dataonly"
MODEL = "qwen2.5-coder:14b"
OLLAMA = "http://127.0.0.1:11434/api/chat"
VERSION = "grounded_plan_repair_v1"
SINGLE_VERSION = "grounded_single_call_repair_v1"
HEARTBEAT_SECONDS = 15
FIELDS = ["id", "db_id", "complexity_bucket", "question", "baseline_sql",
          "plan", "first_sql", "first_error", "pred_sql", "exec_error",
          "exec_match", "column_permutation_match", "latency_sec", "repaired", "variant"]
STOPWORDS = {"about", "after", "along", "also", "between", "country", "different",
             "each", "every", "find", "from", "have", "into", "list", "more",
             "name", "names", "number", "only", "other", "over", "return",
             "show", "than", "that", "their", "there", "these", "this",
             "those", "which", "with", "year"}


def quoted(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def value_hints(sqlite_path, question, limit=12):
    """Find question phrases that exactly match observed text values."""
    hints = []
    question_words = re.findall(r"[\w]+", question.casefold())
    question_text = " " + " ".join(question_words) + " "
    with sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True) as conn:
        # A few Spider TEXT cells contain invalid UTF-8 bytes.
        conn.text_factory = lambda raw: raw.decode("utf-8", "replace")
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for table in tables:
            columns = conn.execute(f"PRAGMA table_info({quoted(table)})").fetchall()
            for col in columns:
                name, kind = col[1], (col[2] or "").upper()
                if not any(t in kind for t in ("TEXT", "CHAR", "CLOB", "VARCHAR")):
                    continue
                sql = (f"SELECT DISTINCT {quoted(name)} FROM {quoted(table)} "
                       f"WHERE {quoted(name)} IS NOT NULL")
                for (value,) in conn.execute(sql):
                    if not isinstance(value, str) or len(value) < 4 or len(value) > 80:
                        continue
                    words = re.findall(r"[\w]+", value.casefold())
                    if not words or (len(words) == 1 and words[0] in STOPWORDS):
                        continue
                    if " " + " ".join(words) + " " in question_text:
                        hints.append((len(value), table, name, value))
    hints.sort(key=lambda item: (-item[0], item[1], item[2], item[3]))
    return [f"{table}.{column} = {value!r}" for _, table, column, value in hints[:limit]]


def ask(messages, max_tokens, stage):
    start = time.monotonic()
    stopped = threading.Event()

    def heartbeat():
        while not stopped.wait(HEARTBEAT_SECONDS):
            print(f"  {stage}: waiting for Ollama ({time.monotonic() - start:.0f}s)", flush=True)

    print(f"  {stage}: request sent to Ollama", flush=True)
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        response = requests.post(OLLAMA, json={
            "model": MODEL, "messages": messages, "stream": False,
            "options": {"temperature": 0, "num_predict": max_tokens},
        }, timeout=300)
    finally:
        stopped.set()
        thread.join()
    response.raise_for_status()
    elapsed = time.monotonic() - start
    print(f"  {stage}: response received in {elapsed:.1f}s", flush=True)
    return response.json()["message"]["content"].strip(), elapsed


def extract_sql(text):
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.I | re.S)
    if match:
        text = match.group(1)
    text = re.sub(r"^\s*(?:SQL|Query)\s*:\s*", "", text, flags=re.I).strip()
    return text.split(";")[0].strip() + ";" if ";" in text else text


def matches_after_column_reorder(gold_rows, pred_rows):
    """Diagnostic only: preserve ordered-column execution match as the score."""
    if not gold_rows or not pred_rows or len(gold_rows) != len(pred_rows):
        return False
    width = len(gold_rows[0])
    if width < 2 or width > 5 or len(pred_rows[0]) != width:
        return False
    gold = Counter(tuple(normalize_cell(cell) for cell in row) for row in gold_rows)
    for order in permutations(range(width)):
        if order == tuple(range(width)):
            continue
        reordered = Counter(tuple(normalize_cell(row[i]) for i in order) for row in pred_rows)
        if reordered == gold:
            return True
    return False


def retry(example, single_call=False):
    schema = load_schema(example, LAYER)
    hints = value_hints(example["sqlite_path"], example["question"])
    grounding = "\n".join(hints) if hints else "No exact text-value matches found."
    context = (f"Schema:\n{schema}\n\nObserved database values matching the question "
               f"(candidates, not required filters):\n{grounding}\n\n"
               f"Question: {example['question']}")
    plan = ""
    t1 = 0.0
    if not single_call:
        plan, t1 = ask([
            {"role": "system", "content": (
                "Plan a SQLite query. In at most 100 words, identify the result columns, "
                "the table and column for each entity or literal, the full join path, "
                "filter logic including AND/OR/NOT and all/any, grouping grain, and "
                "the target of any aggregate or comparison. Do not write SQL.")},
            {"role": "user", "content": context},
        ], 180, f"ID {example['id']} plan")
    sql_system = (
        "Write one read-only SQLite SELECT query and nothing else. Verify every "
        "table, column and join against the schema. Check result-column order, "
        "AND/OR/NOT and all/any logic, grouping grain, and each aggregate or "
        "comparison target before answering. When 'both' refers to two values "
        "in separate related rows, use EXISTS, INTERSECT, or grouped HAVING; "
        "never require one column in one row to equal both values. "
        "For 'not', include rows with no related record when appropriate. "
        "End with a semicolon.")
    if plan:
        sql_system += " Follow the supplied plan only where it agrees with the schema and question."
    sql_context = context + ("\n\nPlan:\n" + plan if plan else "")
    sql_text, t2 = ask([
        {"role": "system", "content": sql_system},
        {"role": "user", "content": sql_context},
    ], 350, f"ID {example['id']} SQL")
    first_sql = extract_sql(sql_text)
    sql = first_sql
    _, error = run_sql(example["sqlite_path"], sql)
    first_error = error or ""
    repaired = False
    elapsed = t1 + t2
    if error:
        repair_text, t3 = ask([
            {"role": "system", "content": (
                "Correct this SQLite query using the schema and SQLite error. "
                "Return one read-only SELECT query only; preserve the question's meaning.")},
            {"role": "user", "content": sql_context
             + f"\n\nInvalid query:\n{sql}\n\nSQLite error: {error}"},
        ], 350, f"ID {example['id']} repair")
        sql = extract_sql(repair_text)
        elapsed += t3
        repaired = True
    pred_rows, final_error = run_sql(example["sqlite_path"], sql)
    gold_rows, gold_error = run_sql(example["sqlite_path"], example["gold_sql"])
    if gold_error:
        raise RuntimeError(f"Gold SQL failed for id={example['id']}: {gold_error}")
    exact_match = rows_match(gold_rows, pred_rows)
    return {"plan": plan, "first_sql": first_sql, "first_error": first_error,
            "pred_sql": sql, "exec_error": final_error or "",
            "exec_match": exact_match,
            "column_permutation_match": (not exact_match and
                                         matches_after_column_reorder(gold_rows, pred_rows)),
            "latency_sec": round(elapsed, 2), "repaired": repaired}


def summarize(rows, failed_total, baseline_correct, variant):
    wins = sum(row["exec_match"] == "True" for row in rows)
    by_bucket = Counter(row["complexity_bucket"] for row in rows if row["exec_match"] == "True")
    return {"variant": variant, "model": MODEL, "baseline_correct": baseline_correct,
            "baseline_failed": failed_total, "retried": len(rows), "recovered": wins,
            "still_wrong": len(rows) - wins,
            "correct_if_unretried_failures_stay_wrong": baseline_correct + wins,
            "recovered_by_bucket": dict(by_bucket),
            "column_permutation_only": sum(row["column_permutation_match"] == "True"
                                           for row in rows),
            "sql_errors_after_retry": sum(bool(row["exec_error"]) for row in rows),
            "repair_attempts": sum(row["repaired"] == "True" for row in rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--single-call", action="store_true",
                        help="Generate SQL immediately; skip the separate planning request")
    parser.add_argument("--max-new", type=int, help="Limit new retries in this invocation")
    parser.add_argument("--dry-run", action="store_true", help="Print one grounded prompt without contacting Ollama")
    args = parser.parse_args()
    if args.max_new is not None and args.max_new < 1:
        parser.error("--max-new must be positive")
    with BASELINE.open(newline="") as source:
        baseline_rows = list(csv.DictReader(source))
    examples = {str(ex["id"]): ex for ex in json.loads(DATASET.read_text())}
    if (len(baseline_rows) != len(examples)
            or {r["id"] for r in baseline_rows} != set(examples)):
        raise RuntimeError("Baseline must contain every unique dataset ID")
    failed = {r["id"]: r for r in baseline_rows if r["exec_match"] != "True"}
    baseline_correct = len(baseline_rows) - len(failed)
    output_path = SINGLE_OUTPUT if args.single_call else OUTPUT
    summary_path = output_path.with_suffix(".summary.json")
    variant = SINGLE_VERSION if args.single_call else VERSION
    done = []
    if output_path.exists():
        with output_path.open(newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames != FIELDS:
                raise RuntimeError("Retry file has an incompatible header")
            done = list(reader)
        if (len({r["id"] for r in done}) != len(done)
                or any(r["id"] not in failed or r["variant"] != variant for r in done)):
            raise RuntimeError("Retry file has duplicate, unexpected, or incompatible rows")
    remaining = sorted((examples[id_] for id_ in failed if id_ not in {r["id"] for r in done}),
                       key=lambda ex: (ex["db_id"], ex["id"]))
    if args.dry_run:
        if remaining:
            ex = remaining[0]
            print(json.dumps({"id": ex["id"], "question": ex["question"],
                              "value_hints": value_hints(ex["sqlite_path"], ex["question"]),
                              "schema": load_schema(ex, LAYER)}, indent=2))
        else:
            print("All failed IDs have already been retried.")
        return
    try:
        requests.get("http://127.0.0.1:11434/api/tags", timeout=5).raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Ollama is unavailable at localhost:11434: {exc}") from exc
    todo = remaining[:args.max_new] if args.max_new else remaining
    calls = "one Ollama response" if args.single_call else "two Ollama responses"
    print(f"Qwen 14B retry ({variant}): {len(done)}/{len(failed)} failed IDs "
          f"already saved; running {len(todo)} now. Each ID requires {calls} "
          "(plus one if SQLite rejects the SQL).", flush=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        if output_path.stat().st_size == 0:
            writer.writeheader()
        try:
            for number, ex in enumerate(todo, 1):
                print(f"[{number}/{len(todo)}] ID {ex['id']} ({ex['db_id']}): "
                      f"{ex['question']}", flush=True)
                result = retry(ex, single_call=args.single_call)
                row = {"id": ex["id"], "db_id": ex["db_id"],
                       "complexity_bucket": ex["complexity_bucket"], "question": ex["question"],
                       "baseline_sql": failed[str(ex["id"])]["pred_sql"], "variant": variant,
                       **result}
                writer.writerow(row)
                output.flush()
                done.append({key: str(value) for key, value in row.items()})
                summary = summarize(done, len(failed), baseline_correct, variant)
                summary_path.write_text(json.dumps(summary, indent=2) + "\n")
                print(f"  ID {ex['id']}: {'RECOVERED' if result['exec_match'] else 'wrong'}; "
                      f"{summary['recovered']}/{summary['retried']} recovered", flush=True)
        except KeyboardInterrupt:
            print(f"\nInterrupted. Saved {len(done)}/{len(failed)} retry rows; "
                  "rerun the same command to resume.", flush=True)
            raise SystemExit(130)
    print(json.dumps(summarize(done, len(failed), baseline_correct, variant), indent=2))


if __name__ == "__main__":
    main()
