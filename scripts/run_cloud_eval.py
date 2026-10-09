"""Evaluate a remote text-to-SQL endpoint on the 1,032 Spider dev questions.

Uses curl for one POST per question. Requests contain the question and schemas;
gold SQL and local SQLite paths are used only for local grading, never sent.
All outputs live under results/cloud/ and never touch local Ollama results.

Example (inspect first; no network request):
  python3 scripts/run_cloud_eval.py --run team_v1 --label model_a --dry-run

Example (endpoint and response contract supplied by the teammate):
  python3 scripts/run_cloud_eval.py --run team_v1 --label model_a \
    --model model_a --endpoint https://example.invalid/query \
    --response-path sql --batch-size 100
"""

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

from run_eval import extract_sql, rows_match, run_sql


ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "data" / "eval_sample.json"
SEMANTICS = ROOT / "data" / "semantic_layer_dataonly"
OUTPUT_ROOT = ROOT / "results" / "cloud"
FIELDS = [
    "id", "db_id", "complexity_bucket", "question", "gold_sql", "pred_sql",
    "raw_response", "exec_error", "exec_match", "latency_sec", "model_id",
]
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
PLACEHOLDERS = {"$id", "$db_id", "$question", "$schema", "$semantic_schema", "$model"}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", help="Lambda Function URL or API Gateway URL")
    parser.add_argument("--run", required=True, help="Experiment name; folder under results/cloud/")
    parser.add_argument("--label", required=True, help="Result file label for this cloud model")
    parser.add_argument("--model", help="Cloud model ID, included in default request payload")
    parser.add_argument("--response-path", default="sql",
                        help="Dotted path to SQL in JSON response, e.g. sql or body.response; '.' for plain text")
    parser.add_argument("--request-template", type=Path,
                        help="JSON body template with exact $question, $schema, $semantic_schema, $db_id, $id, $model placeholders")
    parser.add_argument("--curl-config", type=Path,
                        help="Optional curl config file for authentication headers; keep secrets outside this repo")
    parser.add_argument("--batch-size", type=int, help="Maximum new questions this invocation; omit for all remaining")
    parser.add_argument("--timeout", type=int, default=300, help="Seconds per request (default: 300)")
    parser.add_argument("--retries", type=int, default=0, help="Extra tries after a failed HTTP request")
    parser.add_argument("--dry-run", action="store_true", help="Print first request body and exit without calling curl")
    args = parser.parse_args()
    for name in (args.run, args.label):
        if not NAME_RE.fullmatch(name):
            parser.error("--run and --label must contain only letters, digits, underscores, or hyphens")
    if not args.dry_run and not args.endpoint:
        parser.error("--endpoint is required unless --dry-run is used")
    if args.batch_size is not None and args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    if args.timeout <= 0 or args.retries < 0:
        parser.error("--timeout must be positive and --retries nonnegative")
    if args.curl_config and not args.curl_config.is_file():
        parser.error("--curl-config file does not exist")
    return args


def replace_template(value, variables):
    if isinstance(value, str):
        if value in PLACEHOLDERS:
            key = value[1:]
            if variables[key] is None:
                raise ValueError(f"Template needs {value}, but no --model was supplied")
            return variables[key]
        return value
    if isinstance(value, list):
        return [replace_template(x, variables) for x in value]
    if isinstance(value, dict):
        return {k: replace_template(v, variables) for k, v in value.items()}
    return value


def payload_for(example, args, template=None):
    semantic_path = SEMANTICS / f"{example['db_id']}.sql"
    if not semantic_path.is_file():
        raise FileNotFoundError(f"Missing data-only semantic schema: {semantic_path}")
    variables = {
        "id": example["id"],
        "db_id": example["db_id"],
        "question": example["question"],
        "schema": example["schema_text"],
        "semantic_schema": semantic_path.read_text(),
        "model": args.model,
    }
    if template is not None:
        return replace_template(template, variables)
    payload = {k: variables[k] for k in ("id", "db_id", "question", "schema", "semantic_schema")}
    if args.model:
        payload["model"] = args.model
    return payload


def get_path(response_text, path):
    if path == ".":
        return response_text.strip()
    value = json.loads(response_text)
    for part in path.split("."):
        if isinstance(value, str):
            value = json.loads(value)
        value = value[int(part)] if isinstance(value, list) else value[part]
    if not isinstance(value, str):
        raise ValueError(f"Response path {path!r} must resolve to SQL text, got {type(value).__name__}")
    return value


def call_endpoint(payload, args):
    cmd = [
        "curl", "--silent", "--show-error", "--fail-with-body",
        "--max-time", str(args.timeout), "--request", "POST",
        "--header", "Content-Type: application/json",
        "--data-binary", "@-", "--url", args.endpoint,
    ]
    if args.curl_config:
        cmd.extend(["--config", str(args.curl_config.resolve())])
    body = json.dumps(payload, ensure_ascii=False)
    for attempt in range(args.retries + 1):
        start = time.monotonic()
        proc = subprocess.run(cmd, input=body, text=True, capture_output=True)
        elapsed = time.monotonic() - start
        if proc.returncode == 0:
            return proc.stdout, elapsed
        if attempt == args.retries:
            raise RuntimeError(
                f"curl failed with code {proc.returncode}: "
                f"{(proc.stderr or proc.stdout)[:500]}"
            )
        time.sleep(min(2 ** attempt, 10))
    raise AssertionError("Unreachable")


def existing_rows(path, expected_ids):
    if not path.exists():
        return []
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"Unexpected CSV columns in {path}")
        rows = list(reader)
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)) or not set(ids) <= expected_ids:
        raise ValueError(f"Duplicate or unexpected IDs in {path}")
    return rows


def run_identity(args, template):
    schema_bytes = b"".join(
        p.name.encode() + b"\0" + p.read_bytes() + b"\0"
        for p in sorted(SEMANTICS.glob("*.sql"))
    )
    return {
        "endpoint_sha256": hashlib.sha256(args.endpoint.encode()).hexdigest(),
        "dataset_sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(),
        "semantic_schema_sha256": hashlib.sha256(schema_bytes).hexdigest(),
        "request_template_sha256": hashlib.sha256(
            json.dumps(template, sort_keys=True).encode()
        ).hexdigest(),
        "response_path": args.response_path,
        "model_id": args.model,
    }


def write_summary(path, rows, label, model, total):
    by_bucket = defaultdict(list)
    for row in rows:
        by_bucket[row["complexity_bucket"]].append(row)
    def stats(group):
        n = len(group)
        correct = sum(r["exec_match"] == "True" for r in group)
        return {"total": n, "correct": correct,
                "accuracy": round(correct / n, 4) if n else None}
    result = {
        "label": label,
        "model_id": model,
        "expected": total,
        "complete": len(rows) == total,
        **stats(rows),
        "by_bucket": {k: stats(v) for k, v in sorted(by_bucket.items())},
        "sql_errors": sum(bool(r["exec_error"]) for r in rows),
        "avg_latency_sec": round(sum(float(r["latency_sec"]) for r in rows) / len(rows), 2) if rows else None,
    }
    path.write_text(json.dumps(result, indent=2) + "\n")


def main():
    args = parse_args()
    examples = json.loads(DATASET.read_text())
    expected_ids = {str(ex["id"]) for ex in examples}
    if len(examples) != 1032 or len(expected_ids) != 1032:
        raise RuntimeError("Expected 1,032 Spider dev questions with unique IDs")
    examples.sort(key=lambda ex: (ex["db_id"], ex["id"]))
    template = json.loads(args.request_template.read_text()) if args.request_template else None

    if args.dry_run:
        print(json.dumps(payload_for(examples[0], args, template), indent=2, ensure_ascii=False))
        print(f"\nPrepared {len(examples)} Spider dev requests; no HTTP call or result file written.")
        return

    out_dir = OUTPUT_ROOT / args.run
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"results_{args.label}.csv"
    summary_path = out_dir / f"summary_{args.label}.json"
    identity_path = out_dir / f"config_{args.label}.json"
    identity = run_identity(args, template)
    if identity_path.exists():
        if json.loads(identity_path.read_text()) != identity:
            raise RuntimeError(f"Run configuration changed for {args.label}; choose a new --run or --label")
    elif out_path.exists():
        raise RuntimeError(f"Results exist without a run configuration: {out_path}")
    else:
        identity_path.write_text(json.dumps(identity, indent=2) + "\n")
    rows = existing_rows(out_path, expected_ids)
    done = {r["id"] for r in rows}
    remaining = [ex for ex in examples if str(ex["id"]) not in done]
    todo = remaining[:args.batch_size] if args.batch_size else remaining
    if not todo:
        write_summary(summary_path, rows, args.label, args.model, len(examples))
        print(f"{args.label}: already complete ({len(rows)}/{len(examples)})")
        return

    print(f"{args.label}: {len(rows)}/{len(examples)} saved; sending {len(todo)} requests", flush=True)
    with out_path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if f.tell() == 0:
            writer.writeheader()
        for ex in todo:
            payload = payload_for(ex, args, template)
            response, elapsed = call_endpoint(payload, args)
            try:
                predicted = extract_sql(get_path(response, args.response_path))
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise RuntimeError(f"Cannot read SQL from response for id={ex['id']}: {exc}; "
                                   f"response={response[:300]!r}") from exc
            gold_rows, gold_error = run_sql(ex["sqlite_path"], ex["gold_sql"])
            predicted_rows, sql_error = run_sql(ex["sqlite_path"], predicted) if predicted else (None, "empty prediction")
            match = rows_match(gold_rows, predicted_rows) if gold_error is None else False
            row = {
                "id": ex["id"], "db_id": ex["db_id"],
                "complexity_bucket": ex["complexity_bucket"],
                "question": ex["question"], "gold_sql": ex["gold_sql"],
                "pred_sql": predicted, "raw_response": response[:2000],
                "exec_error": sql_error or "", "exec_match": match,
                "latency_sec": round(elapsed, 2), "model_id": args.model or "",
            }
            writer.writerow(row)
            f.flush()
            rows.append({k: str(v) for k, v in row.items()})
            if len(rows) % 10 == 0:
                correct = sum(r["exec_match"] == "True" for r in rows)
                print(f"{args.label}: {len(rows)}/{len(examples)} correct={correct} ({correct/len(rows):.1%})", flush=True)
    write_summary(summary_path, rows, args.label, args.model, len(examples))
    print(f"Wrote {out_path} and {summary_path}; complete={len(rows)==len(examples)}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        sys.exit(str(exc))
