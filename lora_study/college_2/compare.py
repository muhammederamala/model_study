"""Compare baseline and adapter on identical held-out college_2 IDs."""

import csv
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def read(path):
    if not path.exists():
        raise SystemExit(f"missing results: {path}")
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_id = {row["id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError(f"duplicate ID in {path}")
    return by_id


def main():
    expected = {str(ex["id"]) for ex in json.loads((HERE / "test.json").read_text())}
    base_manifest = json.loads((HERE / "runs/baseline/manifest.json").read_text())
    tuned_manifest = json.loads((HERE / "runs/adapter/manifest.json").read_text())
    without_model = lambda manifest: {key: value for key, value in manifest.items() if key != "model"}
    if without_model(base_manifest) != without_model(tuned_manifest):
        raise ValueError("baseline and adapter used different evaluation inputs")
    base = read(HERE / "runs/baseline/results.csv")
    tuned = read(HERE / "runs/adapter/results.csv")
    if not set(base) <= expected or not set(tuned) <= expected:
        raise ValueError("results contain IDs outside the frozen test split")
    shared = sorted(set(base) & set(tuned), key=int)
    recovered = [int(key) for key in shared if base[key]["exec_match"] != "True"
                 and tuned[key]["exec_match"] == "True"]
    regressed = [int(key) for key in shared if base[key]["exec_match"] == "True"
                 and tuned[key]["exec_match"] != "True"]
    summary = {"test_total": len(expected), "baseline_model": base_manifest["model"],
               "adapter_model": tuned_manifest["model"], "baseline_completed": len(base),
               "adapter_completed": len(tuned), "paired": len(shared),
               "baseline_correct_paired": sum(base[key]["exec_match"] == "True" for key in shared),
               "adapter_correct_paired": sum(tuned[key]["exec_match"] == "True" for key in shared),
               "recovered_ids": recovered, "regressed_ids": regressed,
               "net_gain": len(recovered) - len(regressed)}
    if len(shared) == len(expected):
        summary["baseline_accuracy"] = summary["baseline_correct_paired"] / len(shared)
        summary["adapter_accuracy"] = summary["adapter_correct_paired"] / len(shared)
    output = HERE / "runs/comparison.json"
    output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
