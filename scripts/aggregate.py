"""
Aggregate per-model result CSVs into overall + per-bucket + per-db accuracy
tables, and error breakdowns.

Usage: python3 aggregate.py [lever_name]
  lever_name defaults to "baseline". Reads results/runs/<lever>/results_*.csv,
  writes results/runs/<lever>/summary.json, and appends one row per model to
  results/progress_log.csv (the master cross-lever trend log — one row per
  (date, lever, model) aggregation, so accuracy over time/levers stays
  comparable without digging through individual summary.json files).
"""
import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path("/home/lenovo/Documents/model_study")
RESULTS_DIR = ROOT / "results"
PROGRESS_LOG = RESULTS_DIR / "progress_log.csv"

MODELS = {
    "llama31_8b": "Llama 3.1 8B",
    "gemma2_9b": "Gemma 2 9B",
    "qwen25coder_7b": "Qwen2.5-Coder 7B",
    "sqlcoder_7b": "SQLCoder 7B",
    "qwen25coder_14b": "Qwen2.5-Coder 14B",
    "gemma3_12b": "Gemma 3 12B",
    "deepseekcoderv2_16b": "DeepSeek-Coder-V2 16B",
}

PROGRESS_LOG_FIELDS = [
    "date", "lever", "model", "suffix", "total", "correct", "accuracy",
    "acc_simple", "acc_moderate", "acc_complex", "exec_error_rate", "avg_latency_sec",
]


def load(lever_dir, suffix):
    path = lever_dir / f"results_{suffix}.csv"
    if not path.exists():
        return None
    with open(path) as f:
        return list(csv.DictReader(f))


def append_progress_log(rows):
    file_exists = PROGRESS_LOG.exists()
    with open(PROGRESS_LOG, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PROGRESS_LOG_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def main():
    lever = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    lever_dir = RESULTS_DIR / "runs" / lever
    if not lever_dir.exists():
        print(f"no results yet for lever '{lever}' ({lever_dir})")
        sys.exit(1)

    today = date.today().isoformat()
    summary = {}
    progress_rows = []

    for suffix, label in MODELS.items():
        rows = load(lever_dir, suffix)
        if rows is None:
            print(f"WARNING: no results for {label} ({suffix}) under lever '{lever}', skipping")
            continue

        total = len(rows)
        correct = sum(1 for r in rows if r["exec_match"] == "True")
        exec_errors = sum(1 for r in rows if r["exec_error"])
        avg_latency = sum(float(r["latency_sec"]) for r in rows) / total if total else 0

        by_bucket = defaultdict(lambda: [0, 0])
        by_db = defaultdict(lambda: [0, 0])
        for r in rows:
            b = r["complexity_bucket"]
            by_bucket[b][1] += 1
            by_bucket[b][0] += int(r["exec_match"] == "True")
            d = r["db_id"]
            by_db[d][1] += 1
            by_db[d][0] += int(r["exec_match"] == "True")

        bucket_acc = {k: (v[0] / v[1] if v[1] else 0) for k, v in by_bucket.items()}

        summary[label] = {
            "suffix": suffix,
            "lever": lever,
            "total": total,
            "correct": correct,
            "accuracy": round(correct / total, 4) if total else 0,
            "exec_error_rate": round(exec_errors / total, 4) if total else 0,
            "avg_latency_sec": round(avg_latency, 2),
            "by_bucket": {k: {"correct": v[0], "total": v[1], "accuracy": round(v[0] / v[1], 4)} for k, v in by_bucket.items()},
            "by_db": {k: {"correct": v[0], "total": v[1], "accuracy": round(v[0] / v[1], 4)} for k, v in sorted(by_db.items())},
        }

        progress_rows.append({
            "date": today,
            "lever": lever,
            "model": label,
            "suffix": suffix,
            "total": total,
            "correct": correct,
            "accuracy": round(correct / total, 4) if total else 0,
            "acc_simple": round(bucket_acc.get("simple", 0), 4),
            "acc_moderate": round(bucket_acc.get("moderate", 0), 4),
            "acc_complex": round(bucket_acc.get("complex", 0), 4),
            "exec_error_rate": round(exec_errors / total, 4) if total else 0,
            "avg_latency_sec": round(avg_latency, 2),
        })

    out_path = lever_dir / "summary.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("by_db",)} for k, v in summary.items()}, indent=2))
    print(f"\nwrote {out_path}")

    if progress_rows:
        append_progress_log(progress_rows)
        print(f"appended {len(progress_rows)} rows to {PROGRESS_LOG}")


if __name__ == "__main__":
    main()
