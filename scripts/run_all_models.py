"""Resume the Spider dev evaluation, one Ollama model and batch at a time.

Run from any directory: python3 scripts/run_all_models.py
Interrupt and rerun safely; run_eval.py skips IDs already in each results CSV.
"""

import csv
import argparse
import json
import statistics
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "data" / "eval_sample.json"
RESULTS = ROOT / "results" / "runs" / "spider_baseline"
EVAL = ROOT / "scripts" / "run_eval.py"
AGGREGATE = ROOT / "scripts" / "aggregate.py"
QWEN_INSIGHTS = ROOT / "scripts" / "analyze_qwen14.py"
BATCH_SIZE = 250
MODELS = [
    ("qwen2.5-coder:14b", "qwen25coder_14b"),
    ("qwen2.5-coder:7b", "qwen25coder_7b"),
    ("gemma3:12b", "gemma3_12b"),
    ("deepseek-coder-v2:16b", "deepseekcoderv2_16b"),
    ("gemma2:9b", "gemma2_9b"),
    ("llama3.1:8b", "llama31_8b"),
    ("sqlcoder:7b", "sqlcoder_7b"),
]
# Preserve partial runs while testing a faster candidate.
PAUSED_SUFFIXES = {"qwen25coder_7b", "gemma3_12b", "gemma2_9b"}


def available_models():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as response:
            return {entry["name"] for entry in json.load(response)["models"]}
    except (OSError, ValueError, KeyError) as exc:
        raise RuntimeError(f"Cannot reach Ollama at localhost:11434: {exc}") from exc


def completed_ids(path, expected_ids):
    if not path.exists():
        return set()
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)) or not set(ids) <= expected_ids:
        raise RuntimeError(f"Unexpected or duplicate question IDs in {path}")
    if any(row["raw_response"].startswith("REQUEST_ERROR:") for row in rows):
        raise RuntimeError(f"Request failure already recorded in {path}; review that row before resuming")
    return set(ids)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=[suffix for _, suffix in MODELS],
                        help="Run one model and stop; use its result-file suffix")
    parser.add_argument("--max-new", type=int, metavar="N",
                        help="With --only, save at most N new answers, then stop")
    args = parser.parse_args()
    if args.max_new is not None and (not args.only or args.max_new < 1):
        parser.error("--max-new requires --only and a positive number")
    if args.only in PAUSED_SUFFIXES:
        parser.error(f"{args.only} is paused")

    expected_ids = {str(row["id"]) for row in json.loads(DATASET.read_text())}
    if len(expected_ids) != 1032:
        raise RuntimeError(f"Expected 1032 unique Spider dev questions, found {len(expected_ids)}")

    # Check the service before run_eval.py can record connection failures as wrong answers.
    installed = available_models()
    for model, suffix in MODELS:
        if args.only and suffix != args.only:
            continue
        if suffix in PAUSED_SUFFIXES:
            print(f"{model}: paused; preserving existing results", flush=True)
            continue
        path = RESULTS / f"results_{suffix}.csv"
        done = completed_ids(path, expected_ids)
        starting_count = len(done)
        if len(done) == len(expected_ids):
            print(f"{model}: complete ({len(done)}/{len(expected_ids)})", flush=True)
            if suffix == "qwen25coder_14b":
                subprocess.run([sys.executable, str(QWEN_INSIGHTS)], cwd=ROOT, check=True)
            continue

        # Avoid starting a second local evaluation while one is still running.
        active = subprocess.run(["pgrep", "-af", "scripts/run_eval.py"],
                                capture_output=True, text=True)
        if active.returncode == 0:
            raise RuntimeError("Another run_eval.py process is active. Stop it "
                               "before loading a second model.\n" + active.stdout[:500])

        if model not in installed:
            print(f"Pulling {model}...", flush=True)
            subprocess.run(["ollama", "pull", model], check=True)
            installed = available_models()
            if model not in installed:
                raise RuntimeError(f"{model} is still unavailable after pull")

        while len(done) < len(expected_ids):
            if args.max_new is not None and len(done) - starting_count >= args.max_new:
                break
            available_models()
            print(f"{model}: {len(done)}/{len(expected_ids)}; starting next batch", flush=True)
            batch_size = min(BATCH_SIZE, args.max_new - (len(done) - starting_count)) if args.max_new is not None else BATCH_SIZE
            process = subprocess.Popen(
                [sys.executable, str(EVAL), model, suffix, str(batch_size),
                 "--dataset=dev", "--lever=spider_baseline"],
                cwd=ROOT,
            )
            while True:
                try:
                    return_code = process.wait(timeout=180)
                    break
                except subprocess.TimeoutExpired:
                    current = len(completed_ids(path, expected_ids))
                    print(f"{model}: {current}/{len(expected_ids)} complete", flush=True)
            if return_code:
                raise RuntimeError(f"Evaluation of {model} exited with status {return_code}")
            updated = completed_ids(path, expected_ids)
            if len(updated) <= len(done):
                raise RuntimeError(f"No progress recorded for {model}")
            done = updated
        if len(done) == len(expected_ids):
            print(f"{model}: complete", flush=True)
        else:
            print(f"{model}: probe complete ({len(done) - starting_count} new answers; {len(done)}/{len(expected_ids)} saved)", flush=True)
            with path.open(newline="") as result_file:
                new_rows = list(csv.DictReader(result_file))[starting_count:]
            latencies = [float(row["latency_sec"]) for row in new_rows]
            correct = sum(row["exec_match"].strip().lower() in {"true", "1"} for row in new_rows)
            print(f"{model}: probe median latency={statistics.median(latencies):.1f}s/question; "
                  f"accuracy={correct}/{len(new_rows)} (small sample)", flush=True)
        if suffix == "qwen25coder_14b":
            subprocess.run([sys.executable, str(QWEN_INSIGHTS)], cwd=ROOT, check=True)

    if args.only:
        print(f"Selected model {args.only} stopped; other models untouched.", flush=True)
    elif PAUSED_SUFFIXES:
        print("Selected models complete. Full-roster aggregation skipped because "
              "Qwen 7B is paused and its CSV is partial.", flush=True)
    else:
        subprocess.run([sys.executable, str(AGGREGATE), "spider_baseline"], cwd=ROOT, check=True)
        print("All seven models complete; summary written.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        sys.exit(str(exc))
