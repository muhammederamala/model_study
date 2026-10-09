"""Profile Qwen 14B's Ollama timing without changing evaluation results.

Run on the laptop when no other model evaluation is active:
    python3 scripts/profile_qwen_latency.py
"""

import json
import statistics
import subprocess
import sys
import time

import requests

from run_eval import DATASETS, OLLAMA_CHAT_URL, SEMANTIC_LAYER_DIRS, SYSTEM_PROMPT, load_schema


MODEL = "qwen2.5-coder:14b"
DATABASES = ("battle_death", "world_1", "student_transcripts_tracking")
QUESTIONS_PER_DB = 4


def seconds(response, key):
    return response.get(key, 0) / 1_000_000_000


def main():
    active = subprocess.run(["pgrep", "-af", "scripts/run_eval.py"], capture_output=True, text=True)
    if active.returncode == 0:
        sys.exit("Another model evaluation is active; run this profiler after it finishes.")
    examples = json.loads(DATASETS["dev"].read_text())
    chosen = []
    for db_id in DATABASES:
        matches = sorted((ex for ex in examples if ex["db_id"] == db_id), key=lambda ex: ex["id"])
        chosen.extend(matches[:QUESTIONS_PER_DB])

    print("id db total_s load_s prompt_s generate_s prompt_tokens cached_tokens output_tokens tok_per_s", flush=True)
    records = []
    for ex in chosen:
        schema = load_schema(ex, SEMANTIC_LAYER_DIRS["dev"])
        prompt = f"### Database Schema:\n{schema}\n\n### Question:\n{ex['question']}\n\n### SQL Query:"
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"temperature": 0, "num_predict": 300},
        }
        started = time.monotonic()
        response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        wall = time.monotonic() - started
        load = seconds(data, "load_duration")
        prefill = seconds(data, "prompt_eval_duration")
        generate = seconds(data, "eval_duration")
        output_tokens = data.get("eval_count", 0)
        rate = output_tokens / generate if generate else 0
        print(f"{ex['id']} {ex['db_id']} {wall:.1f} {load:.1f} {prefill:.1f} {generate:.1f} "
              f"{data.get('prompt_eval_count', 0)} {data.get('prompt_eval_cached_count', 'n/a')} "
              f"{output_tokens} {rate:.1f}", flush=True)
        records.append((wall, load, prefill, generate, rate))

    warm = records[1:]
    print("Warm-request medians: "
          + ", ".join(f"{label}={statistics.median(row[index] for row in warm):.1f}"
                      for index, label in enumerate(("total_s", "load_s", "prompt_s", "generate_s", "tok_per_s"))),
          flush=True)


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as exc:
        sys.exit(f"Ollama request failed: {exc}")
