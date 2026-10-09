"""Write the completed Qwen 14B Spider dev failure analysis to insights/.

Run after the CSV has all 1,032 unique question IDs. This script does not
change evaluation results and refuses to publish a report from partial data.
"""

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results" / "runs" / "spider_baseline"
DATASET = ROOT / "data" / "eval_sample.json"
OUTPUT = ROOT / "insights" / "qwen25coder_14b.md"

CONSTRUCTS = {
    "JOIN": r"\bJOIN\b",
    "GROUP BY": r"\bGROUP\s+BY\b",
    "HAVING": r"\bHAVING\b",
    "nested SELECT": r"\bSELECT\b[\s\S]*\bSELECT\b",
    "set operation": r"\b(?:UNION|INTERSECT|EXCEPT)\b",
    "DISTINCT": r"\bDISTINCT\b",
    "AVG or SUM": r"\b(?:AVG|SUM)\s*\(",
}


def read_rows(suffix):
    with (RESULTS / f"results_{suffix}.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    by_id = {row["id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError(f"Duplicate IDs in {suffix}")
    return by_id


def correct(row):
    return row["exec_match"] == "True"


def pct(n, d):
    return f"{100*n/d:.1f}%" if d else "n/a"


def short(text, limit=600):
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def quote(text):
    return text.replace("`", "\\`").replace("|", "\\|")


def sample_lines(rows, limit=5):
    out = []
    for row in rows[:limit]:
        out.extend([
            f"- **ID {row['id']} · {row['db_id']} · {row['complexity_bucket']}**: {short(row['question'], 240)}",
            f"  - Gold: `{quote(short(row['gold_sql']))}`",
            f"  - Qwen: `{quote(short(row['pred_sql']))}`",
        ])
        if row["exec_error"]:
            out.append(f"  - SQLite error: `{quote(short(row['exec_error'], 240))}`")
    return out or ["- None in this category."]


def main():
    expected = {str(row["id"]) for row in json.loads(DATASET.read_text())}
    qwen = read_rows("qwen25coder_14b")
    llama = read_rows("llama31_8b")
    if len(expected) != 1032 or set(qwen) != expected or set(llama) != expected:
        raise RuntimeError(
            f"Need the same 1,032 complete IDs before analysis: "
            f"Qwen={len(qwen)}, Llama={len(llama)}, expected={len(expected)}"
        )

    rows = list(qwen.values())
    q_correct = sum(map(correct, rows))
    l_correct = sum(map(correct, llama.values()))
    wrong = [r for r in rows if not correct(r)]
    invalid = [r for r in wrong if r["exec_error"]]
    valid_wrong = [r for r in wrong if not r["exec_error"]]
    gained = [r for r in rows if correct(r) and not correct(llama[r["id"]])]
    lost = [r for r in rows if not correct(r) and correct(llama[r["id"]])]
    both_wrong = [r for r in rows if not correct(r) and not correct(llama[r["id"]])]

    lines = [
        "# Qwen 2.5 Coder 14B: Spider dev failure analysis",
        "",
        "Source: `results/runs/spider_baseline/results_qwen25coder_14b.csv` "
        "and the same-question Llama CSV. All 1,032 IDs are present and unique.",
        "The prompt uses the database-derived `semantic_layer_dataonly` schema.",
        "Accuracy means matching gold SQL results on one SQLite database; it "
        "does not prove semantic equivalence on every possible database.",
        "",
        "## Outcome",
        "",
        "| Model | Correct / 1,032 | Accuracy |",
        "|---|---:|---:|",
        f"| Qwen 2.5 Coder 14B | {q_correct}/1032 | {pct(q_correct, 1032)} |",
        f"| Llama 3.1 8B | {l_correct}/1032 | {pct(l_correct, 1032)} |",
        "",
        f"Qwen has {len(wrong)} mismatches: {len(invalid)} SQL execution errors "
        f"and {len(valid_wrong)} executable queries with different results.",
        "",
        "| Paired outcome | Questions |",
        "|---|---:|",
        f"| Qwen right, Llama wrong | {len(gained)} |",
        f"| Llama right, Qwen wrong | {len(lost)} |",
        f"| Both wrong | {len(both_wrong)} |",
        f"| Both right | {1032-len(gained)-len(lost)-len(both_wrong)} |",
        "",
        "## Accuracy by local complexity bucket",
        "",
        "These are this project's heuristic buckets, not Spider's official hardness labels.",
        "",
        "| Bucket | Qwen | Llama | Qwen SQL errors |",
        "|---|---:|---:|---:|",
    ]
    for bucket in ("simple", "moderate", "complex"):
        group = [r for r in rows if r["complexity_bucket"] == bucket]
        qc = sum(map(correct, group))
        lc = sum(correct(llama[r["id"]]) for r in group)
        errors = sum(bool(r["exec_error"]) for r in group)
        lines.append(f"| {bucket} | {qc}/{len(group)} ({pct(qc,len(group))}) "
                     f"| {lc}/{len(group)} ({pct(lc,len(group))}) | {errors} |")

    lines.extend(["", "## SQL constructs in gold queries", "",
                  "Construct groups overlap; this is a diagnostic split, not a causal attribution.",
                  "", "| Construct | N | Qwen correct | Llama correct |",
                  "|---|---:|---:|---:|"])
    for label, pattern in CONSTRUCTS.items():
        group = [r for r in rows if re.search(pattern, r["gold_sql"], re.I)]
        qc = sum(map(correct, group))
        lc = sum(correct(llama[r["id"]]) for r in group)
        lines.append(f"| {label} | {len(group)} | {qc} ({pct(qc,len(group))}) "
                     f"| {lc} ({pct(lc,len(group))}) |")

    errors = Counter(r["exec_error"].split(":")[0] for r in invalid)
    lines.extend(["", "## Execution errors", "",
                  "| SQLite error prefix | Count |", "|---|---:|"])
    for error, n in errors.most_common():
        lines.append(f"| {quote(error)} | {n} |")

    by_db = defaultdict(list)
    for r in rows:
        by_db[r["db_id"]].append(r)
    lines.extend(["", "## Databases with the most mismatches", "",
                  "| Database | Qwen correct / N | Llama correct / N |",
                  "|---|---:|---:|"])
    for db, group in sorted(by_db.items(), key=lambda item: sum(not correct(r) for r in item[1]), reverse=True)[:10]:
        qc = sum(map(correct, group))
        lc = sum(correct(llama[r["id"]]) for r in group)
        lines.append(f"| {db} | {qc}/{len(group)} | {lc}/{len(group)} |")

    examples = [
        ("Invalid SQL examples", invalid),
        ("Executable mismatches with nested SELECT", [r for r in valid_wrong if re.search(CONSTRUCTS["nested SELECT"], r["gold_sql"], re.I)]),
        ("Executable mismatches with JOIN", [r for r in valid_wrong if re.search(CONSTRUCTS["JOIN"], r["gold_sql"], re.I)]),
        ("Qwen wins over Llama", gained),
        ("Llama wins over Qwen", lost),
    ]
    for heading, group in examples:
        lines.extend(["", f"## {heading}", "", *sample_lines(group)])

    lines.extend([
        "", "## Interpretation and next review", "",
        "- Inspect representative SQL pairs above before assigning a cause. An "
        "executable mismatch can reflect a wrong join, grouping, filter, "
        "projection, literal, or a questionable gold annotation.",
        "- Compare moderate/complex accuracy with the current annotated "
        "reference, then test one proposed lever at a time on the same IDs.",
        "- Manually review question/gold inconsistencies. Never feed dev gold "
        "SQL or these failure labels into a prompt scored on Spider dev.",
        "",
    ])
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text("\n".join(lines))
    print(f"Wrote {OUTPUT}: {q_correct}/1032 correct, {len(wrong)} mismatches")


if __name__ == "__main__":
    main()
