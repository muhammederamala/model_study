"""Apply the reviewed whitespace/reference audit to baseline, catalog, English results.

Reports only IDs present in all three model runs. Audit rules match
audit_grounded_results.py and do not modify evaluator CSV files.
"""

import csv
import json
from pathlib import Path

from audit_grounded_results import (
    BASELINE, DATASET, GROUNDED, ORDER_INSENSITIVE_COLUMNS,
    normalized_flight_connection, read_rows, run_sql, score_special,
)


ROOT = Path(__file__).resolve().parents[1]
ENGLISH = ROOT / "results/runs/english_semantics/results_qwen25coder_14b.csv"
OUTPUT = ROOT / "results/audits/semantic_variants"


def main():
    examples = json.loads(DATASET.read_text())
    by_id = {str(ex["id"]): ex for ex in examples}
    baseline, _ = read_rows(BASELINE)
    catalog, _ = read_rows(GROUNDED)
    english, _ = read_rows(ENGLISH)
    ids = sorted(set(baseline) & set(catalog) & set(english), key=int)
    if not ids:
        raise ValueError("no shared IDs across baseline, catalog, and English results")

    connection = normalized_flight_connection()
    detail = []
    try:
        for key in ids:
            example = by_id[key]
            rows = [baseline[key], catalog[key], english[key]]
            strict = [row["exec_match"] == "True" for row in rows]
            if example["db_id"] == "flight_2" or key in {
                    "454", "997", *ORDER_INSENSITIVE_COLUMNS}:
                rule, scores = score_special(example, rows[0], rows[1], connection)
                # Reuse the exact audit implementation for the English SQL.
                _, english_score = score_special(example, rows[0], rows[2], connection)
                audited = [scores[0][0], scores[1][0], english_score[1][0]]
            else:
                rule = "strict_unchanged"
                audited = strict
            detail.append({"id": key, "db_id": example["db_id"], "question": example["question"],
                           "audit_rule": rule,
                           "baseline_strict": strict[0], "catalog_strict": strict[1],
                           "english_strict": strict[2],
                           "baseline_audited": audited[0], "catalog_audited": audited[1],
                           "english_audited": audited[2]})
    finally:
        connection.close()

    summary = {"evaluated_shared_ids": len(detail), "total_ids": len(examples),
               "baseline_strict_correct": sum(row["baseline_strict"] for row in detail),
               "catalog_strict_correct": sum(row["catalog_strict"] for row in detail),
               "english_strict_correct": sum(row["english_strict"] for row in detail),
               "baseline_audited_correct": sum(row["baseline_audited"] for row in detail),
               "catalog_audited_correct": sum(row["catalog_audited"] for row in detail),
               "english_audited_correct": sum(row["english_audited"] for row in detail),
               "audit_rules": {rule: sum(row["audit_rule"] == rule for row in detail)
                               for rule in sorted({row["audit_rule"] for row in detail})}}
    if len(detail) == len(examples):
        for label in ("baseline", "catalog", "english"):
            summary[f"{label}_audited_accuracy"] = summary[f"{label}_audited_correct"] / len(detail)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (OUTPUT / "per_question.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(detail[0]))
        writer.writeheader()
        writer.writerows(detail)
    print(f"Audited {len(detail)} shared IDs: baseline {summary['baseline_audited_correct']}, "
          f"catalog {summary['catalog_audited_correct']}, English {summary['english_audited_correct']}.")


if __name__ == "__main__":
    main()
