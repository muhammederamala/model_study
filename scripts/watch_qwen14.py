"""Wait for the externally running Qwen 14B evaluation, then write insights.

This watcher only reads result CSVs; it does not contact Ollama or modify runs.
"""

import csv
import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RESULT = ROOT / "results" / "runs" / "spider_baseline" / "results_qwen25coder_14b.csv"
EXPECTED = {str(row["id"]) for row in json.loads((ROOT / "data" / "eval_sample.json").read_text())}


def main():
    while True:
        if RESULT.exists():
            with RESULT.open(newline="") as f:
                rows = list(csv.DictReader(f))
            ids = {row["id"] for row in rows}
            if len(rows) != len(ids) or not ids <= EXPECTED:
                raise RuntimeError("Qwen result CSV contains duplicate or unexpected IDs")
            if ids == EXPECTED:
                subprocess.run([sys.executable, str(ROOT / "scripts" / "analyze_qwen14.py")],
                               cwd=ROOT, check=True)
                return
        time.sleep(60)


if __name__ == "__main__":
    main()
