"""Audit known Spider reference/data mismatches without changing saved runs.

Run at any time: python3 scripts/audit_grounded_results.py
The strict benchmark score is preserved. This produces a separate paired score
on a temporary, whitespace-normalized flight_2 database and three reviewed
reference cases. Audit rules apply identically to baseline and grounded SQL.
"""

import csv
import hashlib
import io
import json
import sqlite3
from pathlib import Path

from run_eval import rows_match, run_sql


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "results/runs/spider_baseline/results_qwen25coder_14b.csv"
GROUNDED = ROOT / "results/runs/question_grounding/results_qwen25coder_14b.csv"
DATASET = ROOT / "data/eval_sample.json"
OUTPUT = ROOT / "results/audits/grounded_qwen14b"
FLIGHT_DB = ROOT / "data/spider_data/database/flight_2/flight_2.sqlite"
FLIGHT_TRIM_COLUMNS = {
    "airports": ("City", "AirportName", "Country", "CountryAbbrev"),
    "flights": ("SourceAirport", "DestAirport"),
}
# Question-level corrections were reviewed against the schema and SQLite rows.
# They are applied to both model outputs; no model-specific answer is hardcoded.
CORRECTED_REFERENCES = {
    "454": ("SELECT name, date, result FROM battle",
            "Question requests three columns; Spider reference omits result."),
    "997": ("SELECT s.id, s.name FROM death d JOIN ship s "
            "ON d.caused_by_ship_id = s.id GROUP BY s.id, s.name "
            "ORDER BY SUM(d.injured) DESC LIMIT 1",
            "Most total injuries means SUM(injured), not count of death rows."),
}
ORDER_INSENSITIVE_COLUMNS = {
    "63": "Question does not specify whether cylinder count or maximum acceleration comes first."
}
FIELDS = ["id", "db_id", "question", "audit_rule", "baseline_strict", "grounded_strict",
          "baseline_audited", "grounded_audited", "baseline_audit_error", "grounded_audit_error"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    snapshot = path.read_bytes()
    if snapshot and not snapshot.endswith(b"\n"):
        raise ValueError(f"incomplete final CSV row in {path}; retry the audit")
    rows = list(csv.DictReader(io.StringIO(snapshot.decode("utf-8"), newline="")))
    by_id = {row["id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError(f"duplicate ID in {path}")
    return by_id, hashlib.sha256(snapshot).hexdigest()


def strip_literal_whitespace(sql):
    """Trim SQL quoted text in the flight-only audit, preserving SQL escaping."""
    output = []
    index = 0
    while index < len(sql):
        quote = sql[index]
        if quote not in "'\"":
            output.append(quote)
            index += 1
            continue
        index += 1
        body = []
        closed = False
        while index < len(sql):
            if sql[index] == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    body.append(quote * 2)
                    index += 2
                    continue
                index += 1
                closed = True
                break
            body.append(sql[index])
            index += 1
        if not closed:
            raise ValueError("unterminated SQL quoted text")
        output.append(quote + "".join(body).strip() + quote)
    return "".join(output)


def normalized_flight_connection():
    source = sqlite3.connect(f"file:{FLIGHT_DB}?mode=ro", uri=True)
    target = sqlite3.connect(":memory:")
    try:
        source.backup(target)
    finally:
        source.close()
    for table, columns in FLIGHT_TRIM_COLUMNS.items():
        for column in columns:
            target.execute(f'UPDATE "{table}" SET "{column}" = TRIM("{column}") '
                           f'WHERE "{column}" IS NOT NULL')
    target.commit()
    target.execute("PRAGMA query_only = 1")
    return target


def execute(connection, sql):
    try:
        return connection.execute(sql).fetchall(), ""
    except sqlite3.Error as error:
        return None, str(error)


def score_special(example, baseline, grounded, flight_connection):
    key = str(example["id"])
    if example["db_id"] == "flight_2":
        rule = "flight_2_whitespace_normalized"
        gold, error = execute(flight_connection, strip_literal_whitespace(example["gold_sql"]))
        if error:
            raise RuntimeError(f"normalized gold SQL failed for ID {key}: {error}")
        scored = []
        for row in (baseline, grounded):
            try:
                pred, pred_error = execute(flight_connection,
                                           strip_literal_whitespace(row["pred_sql"]))
            except ValueError as error:
                pred, pred_error = None, str(error)
            scored.append((rows_match(gold, pred), pred_error))
        return rule, scored

    path = example["sqlite_path"]
    if key in CORRECTED_REFERENCES:
        rule = "corrected_reference"
        gold_sql, _ = CORRECTED_REFERENCES[key]
    else:
        rule = "unspecified_column_order"
        gold_sql = example["gold_sql"]
    gold, error = run_sql(path, gold_sql)
    if error:
        raise RuntimeError(f"audited gold SQL failed for ID {key}: {error}")
    scored = []
    for row in (baseline, grounded):
        pred, pred_error = run_sql(path, row["pred_sql"]) if row["pred_sql"] else (None, "empty SQL")
        good = rows_match(gold, pred)
        if key in ORDER_INSENSITIVE_COLUMNS and pred and len(pred[0]) == 2:
            good = good or rows_match(gold, [tuple(reversed(cells)) for cells in pred])
        scored.append((good, pred_error or ""))
    return rule, scored


def main():
    examples = json.loads(DATASET.read_text())
    by_id = {str(ex["id"]): ex for ex in examples}
    baseline, baseline_hash = read_rows(BASELINE)
    grounded, grounded_hash = read_rows(GROUNDED)
    if set(baseline) != set(by_id) or not set(grounded) <= set(by_id):
        raise ValueError("result IDs do not match evaluation dataset")
    flight_connection = normalized_flight_connection()
    detail = []
    try:
        for key in sorted(grounded, key=int):
            example = by_id[key]
            old_base, old_ground = baseline[key], grounded[key]
            base_strict = old_base["exec_match"] == "True"
            ground_strict = old_ground["exec_match"] == "True"
            if example["db_id"] == "flight_2" or key in CORRECTED_REFERENCES or key in ORDER_INSENSITIVE_COLUMNS:
                rule, scored = score_special(example, old_base, old_ground, flight_connection)
                (base_audited, base_error), (ground_audited, ground_error) = scored
            else:
                rule = "strict_unchanged"
                base_audited, ground_audited = base_strict, ground_strict
                base_error = ground_error = ""
            detail.append({"id": key, "db_id": example["db_id"], "question": example["question"],
                           "audit_rule": rule, "baseline_strict": base_strict,
                           "grounded_strict": ground_strict, "baseline_audited": base_audited,
                           "grounded_audited": ground_audited,
                           "baseline_audit_error": base_error, "grounded_audit_error": ground_error})
    finally:
        flight_connection.close()
    summary = {"paired_ids": len(detail), "total_ids": len(examples),
               "baseline_strict_correct": sum(row["baseline_strict"] for row in detail),
               "grounded_strict_correct": sum(row["grounded_strict"] for row in detail),
               "baseline_audited_correct": sum(row["baseline_audited"] for row in detail),
               "grounded_audited_correct": sum(row["grounded_audited"] for row in detail),
               "baseline_strict_to_audited_gains": sum(not row["baseline_strict"] and row["baseline_audited"] for row in detail),
               "baseline_strict_to_audited_losses": sum(row["baseline_strict"] and not row["baseline_audited"] for row in detail),
               "grounded_strict_to_audited_gains": sum(not row["grounded_strict"] and row["grounded_audited"] for row in detail),
               "grounded_strict_to_audited_losses": sum(row["grounded_strict"] and not row["grounded_audited"] for row in detail),
               "audit_rules": {rule: sum(row["audit_rule"] == rule for row in detail)
                               for rule in sorted({row["audit_rule"] for row in detail})},
               "inputs_sha256": {str(DATASET.relative_to(ROOT)): digest(DATASET),
                                 str(BASELINE.relative_to(ROOT)): baseline_hash,
                                 str(GROUNDED.relative_to(ROOT)): grounded_hash,
                                 str(FLIGHT_DB.relative_to(ROOT)): digest(FLIGHT_DB),
                                 str(Path(__file__).relative_to(ROOT)): digest(Path(__file__))},
               "reference_corrections": {key: {"sql": sql, "reason": reason}
                                         for key, (sql, reason) in CORRECTED_REFERENCES.items()},
               "order_insensitive_cases": ORDER_INSENSITIVE_COLUMNS}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (OUTPUT / "per_question.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(detail)
    print(f"Audited {len(detail)}/{len(examples)} paired IDs. "
          f"Strict: baseline {summary['baseline_strict_correct']}, grounded {summary['grounded_strict_correct']}; "
          f"audited: baseline {summary['baseline_audited_correct']}, "
          f"grounded {summary['grounded_audited_correct']}. -> {OUTPUT}")


if __name__ == "__main__":
    main()
