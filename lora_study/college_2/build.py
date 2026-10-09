"""Create the isolated, fixed college_2 LoRA study inputs."""

import argparse
import hashlib
import json
import random
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_semantic_catalog import build_one, normalize, text_column
from build_semantic_schema import build_semantic_schema
from prepare_dataset import sql_complexity_bucket


DB_ID = "college_2"
SOURCE = ROOT / "data/spider_data/train_spider.json"
TABLES = ROOT / "data/spider_data/tables.json"
SQLITE = ROOT / f"data/spider_data/database/{DB_ID}/{DB_ID}.sqlite"
SEED = 42


def skeleton(sql):
    """Keep paraphrases and literal variants of the same SQL in one split."""
    sql = re.sub(r"'[^']*'|\"[^\"]*\"", "<literal>", sql.casefold())
    sql = re.sub(r"(?<![a-z_])\d+(?:\.\d+)?(?![a-z_])", "<number>", sql)
    return " ".join(sql.split())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="replace existing split and assets")
    args = parser.parse_args()
    outputs = [HERE / f"{part}.json" for part in ("train", "validation", "test")]
    outputs += [HERE / "schema.sql", HERE / "catalog.json", HERE / "split_manifest.json"]
    if not args.force and any(path.exists() for path in outputs):
        parser.error("study inputs already exist; use --force only before any evaluation")
    rows = [row for row in json.loads(SOURCE.read_text()) if row["db_id"] == DB_ID]
    entry = next(row for row in json.loads(TABLES.read_text()) if row["db_id"] == DB_ID)
    groups = defaultdict(list)
    for source_id, row in enumerate(json.loads(SOURCE.read_text())):
        if row["db_id"] != DB_ID:
            continue
        groups[skeleton(row["query"])].append({
            "id": source_id, "db_id": DB_ID, "question": row["question"],
            "gold_sql": row["query"], "sqlite_path": str(SQLITE),
            "complexity_bucket": sql_complexity_bucket(row["query"]),
        })
    assert sum(map(len, groups.values())) == len(rows) == 170
    shuffled = list(groups.values())
    random.Random(SEED).shuffle(shuffled)
    splits = {"train": [], "validation": [], "test": []}
    for group in shuffled:
        if len(splits["test"]) < 26:
            part = "test"
        elif len(splits["validation"]) < 26:
            part = "validation"
        else:
            part = "train"
        splits[part].extend(group)
    if len(splits["train"]) < 100:
        raise ValueError("too few training examples after grouped split")
    for part, examples in splits.items():
        examples.sort(key=lambda ex: ex["id"])
        (HERE / f"{part}.json").write_text(json.dumps(examples, indent=2) + "\n")
    nonunique_keys = []
    with sqlite3.connect(f"file:{SQLITE}?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA query_only = 1")
        schema = build_semantic_schema(DB_ID, entry, connection, include_usage=False)
        # Spider's single-column PK labels are sometimes non-unique in this
        # populated database. Do not state them as SQL constraints in prompts.
        for index in entry.get("primary_keys", []):
            table_index, column = entry["column_names_original"][index]
            table = entry["table_names_original"][table_index]
            quoted_table = '"' + table.replace('"', '""') + '"'
            quoted_column = '"' + column.replace('"', '""') + '"'
            total, distinct = connection.execute(
                f"SELECT COUNT(*), COUNT(DISTINCT {quoted_column}) FROM {quoted_table}").fetchone()
            if total != distinct:
                nonunique_keys.append((table, column))
                start = schema.index(f"CREATE TABLE {table} (")
                end = schema.index("\n);", start)
                block = schema[start:end]
                pattern = rf"(?m)^(  {re.escape(column)} [A-Z]+) PRIMARY KEY"
                block, count = re.subn(pattern, r"\1", block)
                if count != 1:
                    raise ValueError(f"could not correct non-unique key {table}.{column}")
                schema = schema[:start] + block + schema[end:]
    (HERE / "schema.sql").write_text(schema + "\n")
    catalog = build_one(DB_ID, SQLITE)
    for table, column in nonunique_keys:
        entity = catalog["entities"][table]
        entity["primary_key_columns"].remove(column)
        entity["columns"][column].pop("primary_key", None)
        entity.setdefault("declared_nonunique_key_columns", []).append(column)
    # The shared builder excludes one-character strings. Retain real short
    # codes here; grounding uses them only when the question quotes the code.
    seen = {(v["table"], v["column"], v["value"]) for v in catalog["values"]}
    with sqlite3.connect(f"file:{SQLITE}?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA query_only = 1")
        for table, entity in catalog["entities"].items():
            declared = {row[1].casefold(): row[2] for row in connection.execute(
                f'PRAGMA table_info("{table}")')}
            for column, detail in entity["columns"].items():
                if not text_column(declared[column.casefold()], detail.get("type")):
                    continue
                quoted_table = '"' + table.replace('"', '""') + '"'
                quoted_column = '"' + column.replace('"', '""') + '"'
                query = (f"SELECT DISTINCT {quoted_column} FROM {quoted_table} "
                         f"WHERE typeof({quoted_column})='text' "
                         f"AND length(trim({quoted_column}))=1")
                for (value,) in connection.execute(query):
                    key = (table, column, value)
                    if key not in seen and normalize(value):
                        catalog["values"].append({"table": table, "column": column,
                                                  "value": value, "key": normalize(value)})
                        seen.add(key)
    catalog["values"].sort(key=lambda item: (item["key"], item["table"], item["column"], item["value"]))
    catalog["status"] = "structurally_reviewed_for_college_2_pilot"
    catalog["reviewed_notes"] = "reviewed_semantics.md"
    (HERE / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n")
    manifest = {"db_id": DB_ID, "seed": SEED, "source": str(SOURCE.relative_to(ROOT)),
                "source_sha256": digest(SOURCE), "tables_sha256": digest(TABLES),
                "sqlite_sha256": digest(SQLITE),
                "split_method": "group by normalized SQL with literals masked; random seed 42",
                "counts": {part: len(examples) for part, examples in splits.items()},
                "schema_sha256": digest(HERE / "schema.sql"),
                "catalog_sha256": digest(HERE / "catalog.json")}
    (HERE / "split_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Prepared college_2:", manifest["counts"])


if __name__ == "__main__":
    main()
