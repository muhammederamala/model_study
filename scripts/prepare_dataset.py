"""
Extract Spider dev set + SQLite databases, build compact schema DDL text per db,
and sample a stratified subset of questions for the study.

SAMPLE_SIZE = 1034: this is the full dev.json split (all 20 databases), not a
subsample. Kept as a "target sample size" rather than "use everything" because
the stratified-sample + top-up logic below naturally caps at however many
examples survive the gold-SQL-execution sanity check, whether that's less
than, equal to, or (harmlessly) more than the literal count in dev.json.
Original quick-study sample size was 150 (149 after verification) — see
results/ for anything generated against that smaller sample; this is the
2026-09-29 baseline reset to the full dev split.
"""
import json
import random
import sqlite3
import zipfile
from pathlib import Path

ROOT = Path("/home/lenovo/Documents/model_study")
DATA = ROOT / "data"
ZIP_PATH = DATA / "spider_data.zip"
EXTRACT_DIR = DATA / "spider_data"

SAMPLE_SIZE = 1034
SEED = 42


def extract():
    if not EXTRACT_DIR.exists():
        with zipfile.ZipFile(ZIP_PATH) as zf:
            zf.extractall(DATA)
    print("extracted to", EXTRACT_DIR)


def find_file(name):
    matches = list(EXTRACT_DIR.rglob(name))
    if not matches:
        raise FileNotFoundError(name)
    return matches[0]


def build_schema_text(table_entry):
    """Build a compact CREATE-TABLE-style schema description from Spider's tables.json entry."""
    db_id = table_entry["db_id"]
    table_names = table_entry["table_names_original"]
    col_names = table_entry["column_names_original"]  # [(table_idx, col_name), ...], -1 idx = '*'
    col_types = table_entry["column_types"]
    pk = set(table_entry.get("primary_keys", []))
    fks = table_entry.get("foreign_keys", [])

    cols_by_table = {i: [] for i in range(len(table_names))}
    for col_idx, (t_idx, c_name) in enumerate(col_names):
        if t_idx == -1:
            continue
        cols_by_table[t_idx].append((col_idx, c_name, col_types[col_idx]))

    fk_lines = []
    for src_col, tgt_col in fks:
        src_t, src_c = col_names[src_col]
        tgt_t, tgt_c = col_names[tgt_col]
        fk_lines.append(
            f"-- FOREIGN KEY: {table_names[src_t]}.{src_c} REFERENCES {table_names[tgt_t]}.{tgt_c}"
        )

    lines = []
    for t_idx, tname in enumerate(table_names):
        col_defs = []
        for col_idx, cname, ctype in cols_by_table[t_idx]:
            pk_mark = " PRIMARY KEY" if col_idx in pk else ""
            col_defs.append(f"{cname} {ctype.upper()}{pk_mark}")
        lines.append(f"CREATE TABLE {tname} (\n  " + ",\n  ".join(col_defs) + "\n);")

    schema_text = "\n".join(lines)
    if fk_lines:
        schema_text += "\n" + "\n".join(fk_lines)
    return schema_text


def sql_complexity_bucket(query: str) -> str:
    """Rough complexity proxy (NOT the official Spider hardness classifier)."""
    q = query.lower()
    score = 0
    score += q.count(" join ")
    score += q.count("group by")
    score += q.count("having")
    score += q.count("order by")
    score += q.count("union") + q.count("intersect") + q.count("except")
    score += q.count("select") - 1  # nested subqueries
    score += sum(q.count(fn) for fn in ["count(", "sum(", "avg(", "min(", "max("])
    if score <= 1:
        return "simple"
    elif score <= 3:
        return "moderate"
    else:
        return "complex"


def main():
    extract()
    dev_path = find_file("dev.json")
    tables_path = find_file("tables.json")
    db_dir = find_file("database").resolve() if False else None
    # locate the 'database' directory (contains one subfolder per db_id)
    db_dirs = [p for p in EXTRACT_DIR.rglob("database") if p.is_dir()]
    db_root = db_dirs[0]

    dev = json.loads(dev_path.read_text())
    tables = {t["db_id"]: t for t in json.loads(tables_path.read_text())}

    print(f"dev examples: {len(dev)}, dbs in tables.json: {len(tables)}")

    # attach complexity bucket + verify sqlite db exists and gold query executes
    usable = []
    skipped = 0
    for ex in dev:
        db_id = ex["db_id"]
        sqlite_path = db_root / db_id / f"{db_id}.sqlite"
        if not sqlite_path.exists():
            skipped += 1
            continue
        ex["_bucket"] = sql_complexity_bucket(ex["query"])
        ex["_sqlite_path"] = str(sqlite_path)
        usable.append(ex)

    print(f"usable examples (sqlite db found): {len(usable)}, skipped: {skipped}")

    # stratified sample: proportional across (db_id, bucket)
    random.seed(SEED)
    random.shuffle(usable)

    by_bucket = {"simple": [], "moderate": [], "complex": []}
    for ex in usable:
        by_bucket[ex["_bucket"]].append(ex)

    for b, lst in by_bucket.items():
        print(f"  bucket={b}: {len(lst)} available")

    target_per_bucket = {
        "simple": int(SAMPLE_SIZE * 0.35),
        "moderate": int(SAMPLE_SIZE * 0.40),
    }
    target_per_bucket["complex"] = SAMPLE_SIZE - target_per_bucket["simple"] - target_per_bucket["moderate"]

    sample = []
    for b, n in target_per_bucket.items():
        pool = by_bucket[b]
        sample.extend(pool[: min(n, len(pool))])

    # if under target due to shortage in some bucket, top up from remaining pool
    if len(sample) < SAMPLE_SIZE:
        used_ids = {id(ex) for ex in sample}
        remaining = [ex for ex in usable if id(ex) not in used_ids]
        random.shuffle(remaining)
        sample.extend(remaining[: SAMPLE_SIZE - len(sample)])

    random.shuffle(sample)
    print(f"final sample size: {len(sample)}")

    # verify gold SQL actually executes on its db (sanity check)
    verified = []
    exec_errors = 0
    for ex in sample:
        try:
            conn = sqlite3.connect(f"file:{ex['_sqlite_path']}?mode=ro", uri=True, timeout=5)
            cur = conn.cursor()
            cur.execute(ex["query"])
            cur.fetchall()
            conn.close()
            verified.append(ex)
        except Exception as e:
            exec_errors += 1

    print(f"gold-SQL-verified: {len(verified)}, gold exec errors (dropped): {exec_errors}")

    out = []
    for i, ex in enumerate(verified):
        db_id = ex["db_id"]
        schema_text = build_schema_text(tables[db_id])
        out.append({
            "id": i,
            "db_id": db_id,
            "question": ex["question"],
            "gold_sql": ex["query"],
            "complexity_bucket": ex["_bucket"],
            "sqlite_path": ex["_sqlite_path"],
            "schema_text": schema_text,
        })

    out_path = DATA / "eval_sample.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"wrote {len(out)} examples to {out_path}")

    # bucket distribution summary
    from collections import Counter
    print("final bucket distribution:", Counter(e["complexity_bucket"] for e in out))
    print("distinct dbs used:", len(set(e["db_id"] for e in out)))


if __name__ == "__main__":
    main()
