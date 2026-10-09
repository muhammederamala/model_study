"""
Run text-to-SQL generation for each model against the sampled Spider questions,
execute predicted SQL against the ground-truth SQLite db, and grade via
execution accuracy (order-insensitive multiset-of-rows comparison against gold).

Usage: python3 run_eval.py <model_name_in_ollama> <output_csv_suffix> [batch_size] [--lever=<name>]

Batching / resume behavior (added for the 1032-question full-dev-split baseline,
run in batches rather than one multi-hour sitting):
  - Results always APPEND to the same results_<suffix>.csv, never overwrite it.
  - Questions already present in that file (matched by id) are skipped, so
    re-running the exact same command resumes with the next not-yet-done batch
    instead of duplicating rows or starting over.
  - <batch_size> is optional; omit it to process all remaining questions in
    one run (the original all-at-once behavior, just now resume-safe/append-only
    instead of overwrite-on-every-run).

Lever tracking:
  - --lever=<name> controls which subfolder under results/runs/ this writes to,
    e.g. --lever=baseline -> results/runs/baseline/results_<suffix>.csv,
    --lever=semantic_layer -> results/runs/semantic_layer/results_<suffix>.csv.
    Defaults to "baseline" if omitted. Each lever is a separate, independently
    resumable/append-safe set of files, so switching prompting strategies never
    overwrites a previous lever's results, and aggregate.py can be pointed at
    any one lever's folder to compare accuracy across levers.
"""
import csv
import json
import re
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path("/home/lenovo/Documents/model_study")
DATASETS = {
    # The real Spider dev split. NOTE: the semantic layer is mined from these
    # questions' gold SQL, so grading a semantic-layer-prompted model on this
    # set is LEAKY — the prompt encodes the shape of the answers. Use it only
    # for a deliberately-labelled upper-bound number, never as the headline.
    "dev": ROOT / "data" / "eval_sample.json",
    # Our own generated questions against the same 20 databases. Nothing here
    # fed the semantic layer, so this is the honest evaluation target.
    "invented": ROOT / "data" / "invented_eval.json",
}
DEFAULT_DATASET = "invented"

# Which semantic-layer variant is SAFE for which dataset:
#   dev      -> dataonly. Sample values / ranges / row counts / FK quirks come
#               from database contents, never from questions or gold SQL, so
#               there is no leakage against the real Spider questions.
#   invented -> full. Adds usage patterns mined from dev's gold SQL, which is
#               fine here because we are not grading on dev questions.
SEMANTIC_LAYER_DIRS = {
    "dev": ROOT / "data" / "semantic_layer_dataonly",
    "invented": ROOT / "data" / "semantic_layer",
}
RESULTS_DIR = ROOT / "results"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"

# 2026-09-29: the plain-schema-string baseline was abandoned before a full run
# (too costly to run twice at 1032 questions x 7 models) in favor of starting
# straight from the semantic-layer-annotated schema — see levers/baseline.md.
# So "baseline" now means "semantic layer", not "bare CREATE TABLE strings".
# Falls back to the plain schema_text from eval_sample.json if a given db_id
# has no generated semantic_layer/<db_id>.sql (shouldn't happen for the current
# 20-db eval sample, but fails safe rather than crashing the run).
def load_schema(ex: dict, layer_dir: Path) -> str:
    path = layer_dir / f"{ex['db_id']}.sql"
    if path.exists():
        return path.read_text()
    print(f"WARNING: no semantic layer file for db_id={ex['db_id']!r} in {layer_dir.name}, "
          f"falling back to plain schema_text")
    return ex["schema_text"]

SYSTEM_PROMPT = (
    "You are an expert SQLite developer. Given a database schema and a natural "
    "language question, output ONLY the SQL query that answers the question. "
    "Do not include explanations, comments, or markdown code fences. "
    "Output a single valid SQLite query terminated with a semicolon."
)

# Defog SQLCoder is a raw completion model (Ollama template is a bare passthrough,
# no chat roles) - it needs its own documented prompt format via /api/generate.
SQLCODER_PROMPT_TEMPLATE = """### Task
Generate a SQL query to answer the following question:
`{question}`

### Database Schema
This query will run on a database whose schema is represented in this string:
{schema}

### Answer
Given the database schema, here is the SQL query that answers `{question}`:
```sql
"""

SQL_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_sql(text: str) -> str:
    text = text.strip()
    m = SQL_FENCE_RE.search(text)
    if m:
        text = m.group(1).strip()
    # drop leading labels like "SQL:" or "Query:"
    text = re.sub(r"^\s*(sql|query)\s*:\s*", "", text, flags=re.IGNORECASE)
    # if multiple statements/lines of prose slipped in, take up to first semicolon-terminated statement
    if ";" in text:
        text = text.split(";")[0] + ";"
    return text.strip()


def query_model(model: str, schema_text: str, question: str, timeout=300):
    if model.startswith("sqlcoder"):
        prompt = SQLCODER_PROMPT_TEMPLATE.format(question=question, schema=schema_text)
        payload = {
            "model": model,
            "prompt": prompt,
            "raw": True,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 300, "stop": ["```", "<|endoftext|>"]},
        }
        t0 = time.time()
        resp = requests.post(OLLAMA_GENERATE_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        elapsed = time.time() - t0
        content = resp.json()["response"]
        return extract_sql(content), elapsed, content

    user_prompt = f"### Database Schema:\n{schema_text}\n\n### Question:\n{question}\n\n### SQL Query:"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": 0, "num_predict": 300},
    }
    t0 = time.time()
    resp = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=timeout)
    resp.raise_for_status()
    elapsed = time.time() - t0
    content = resp.json()["message"]["content"]
    return extract_sql(content), elapsed, content


def run_sql(sqlite_path: str, sql: str, timeout=5):
    try:
        conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True, timeout=timeout)
        conn.execute("PRAGMA query_only = 1;")
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
        return rows, None
    except Exception as e:
        return None, str(e)


def normalize_cell(v):
    if isinstance(v, float):
        return round(v, 4)
    if v is None:
        return None
    return str(v).strip().lower()


def rows_match(gold_rows, pred_rows) -> bool:
    if gold_rows is None or pred_rows is None:
        return False
    g = Counter(tuple(normalize_cell(c) for c in row) for row in gold_rows)
    p = Counter(tuple(normalize_cell(c) for c in row) for row in pred_rows)
    return g == p


def main():
    lever = "baseline"
    dataset = DEFAULT_DATASET
    positional = []
    for arg in sys.argv[1:]:
        if arg.startswith("--lever="):
            lever = arg.split("=", 1)[1]
        elif arg.startswith("--dataset="):
            dataset = arg.split("=", 1)[1]
        else:
            positional.append(arg)

    if len(positional) not in (2, 3) or dataset not in DATASETS:
        print("usage: run_eval.py <ollama_model_name> <output_suffix> [batch_size] "
              f"[--lever=<name>] [--dataset={'|'.join(DATASETS)}]")
        sys.exit(1)
    model = positional[0]
    suffix = positional[1]
    batch_size = int(positional[2]) if len(positional) == 3 else None

    sample_path = DATASETS[dataset]
    layer_dir = SEMANTIC_LAYER_DIRS[dataset]
    examples = json.loads(sample_path.read_text())
    # Sort by db_id (not shuffled) so consecutive requests share the same
    # schema prefix. The eval sample is stored pre-shuffled across dbs;
    # processing in that order means the inference server's prompt-prefix
    # cache misses on almost every request once the schema is large (measured:
    # ~37s/q shuffled vs ~11s/q grouped on llama3.1:8b, see CLAUDE.md
    # Changelog 2026-09-29). Order has no effect on grading — each question is
    # scored independently — so this is free speedup, not a methodology change.
    examples.sort(key=lambda e: (e["db_id"], e["id"]))
    print(f"[{model}] dataset={dataset} ({len(examples)} questions) lever={lever} schema_layer={layer_dir.name}")
    lever_dir = RESULTS_DIR / "runs" / lever
    lever_dir.mkdir(parents=True, exist_ok=True)
    out_path = lever_dir / f"results_{suffix}.csv"

    fieldnames = [
        "id", "db_id", "complexity_bucket", "question", "gold_sql", "pred_sql",
        "raw_response", "exec_error", "exec_match", "latency_sec",
    ]

    # Resume support: skip ids already recorded for this suffix, and total
    # accuracy accounting below folds in prior batches, not just this run's.
    done_ids = set()
    prior_total = 0
    prior_correct = 0
    file_exists = out_path.exists()
    if file_exists:
        with open(out_path, newline="") as f:
            for row in csv.DictReader(f):
                done_ids.add(row["id"])
                prior_total += 1
                prior_correct += int(row["exec_match"] == "True")

    remaining = [ex for ex in examples if str(ex["id"]) not in done_ids]
    todo = remaining[:batch_size] if batch_size is not None else remaining

    if not todo:
        print(f"[{model}] nothing to do — all {len(examples)} questions already in {out_path}")
        return

    print(
        f"[{model}] {len(done_ids)}/{len(examples)} already done, "
        f"{len(remaining)} remaining, running batch of {len(todo)} now -> {out_path}"
    )

    with open(out_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        n_correct = prior_correct
        for i, ex in enumerate(todo):
            try:
                pred_sql, elapsed, raw = query_model(model, load_schema(ex, layer_dir), ex["question"])
            except Exception as e:
                # A transport/model timeout is not a wrong SQL answer. Abort
                # without writing this ID so a resumed batch can retry it.
                raise RuntimeError(
                    f"Model request failed for id={ex['id']} db={ex['db_id']}: {e}"
                ) from e

            gold_rows, gold_err = run_sql(ex["sqlite_path"], ex["gold_sql"])
            pred_rows, pred_err = run_sql(ex["sqlite_path"], pred_sql) if pred_sql else (None, "empty prediction")

            match = rows_match(gold_rows, pred_rows) if gold_err is None else False
            n_correct += int(match)

            writer.writerow({
                "id": ex["id"],
                "db_id": ex["db_id"],
                "complexity_bucket": ex["complexity_bucket"],
                "question": ex["question"],
                "gold_sql": ex["gold_sql"],
                "pred_sql": pred_sql,
                "raw_response": raw[:500],
                "exec_error": pred_err or "",
                "exec_match": match,
                "latency_sec": round(elapsed, 2),
            })
            f.flush()

            done_so_far = prior_total + i + 1
            if (i + 1) % 10 == 0:
                print(
                    f"[{model}] batch {i+1}/{len(todo)}  "
                    f"overall {done_so_far}/{len(examples)}  running_acc={n_correct/done_so_far:.3f}"
                )

    total_done = prior_total + len(todo)
    print(
        f"[{model}] BATCH DONE. {total_done}/{len(examples)} total complete, "
        f"cumulative accuracy={n_correct/total_done:.3f}  ->  {out_path}"
    )
    if total_done < len(examples):
        print(f"[{model}] {len(examples) - total_done} remaining — re-run the same command to continue.")


if __name__ == "__main__":
    main()
