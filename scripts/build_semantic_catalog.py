"""Build source-grounded semantic catalogs for the Spider evaluation databases.

Combines existing schema metadata with a bounded index of observed SQLite text
values. It reads no questions or gold SQL. Generated files are safe to use as
retrieval context on Spider dev; business meanings remain unconfirmed.

Usage: python3 scripts/build_semantic_catalog.py [--db-id DB_ID]
"""

import argparse
import copy
import json
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEMANTICS = ROOT / "data/semantics_json"
DATAONLY = ROOT / "data/semantic_layer_dataonly"
DATABASES = ROOT / "data/spider_data/database"
OUTPUT = ROOT / "data/semantic_catalog"
MAX_DISTINCT_PER_COLUMN = 25000
MAX_VALUE_LENGTH = 80
TEXT_TYPES = ("TEXT", "CHAR", "CLOB", "VARCHAR", "DATE", "TIME")


def quote(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def normalize(value):
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value).replace("_", " ")
    return " ".join(re.findall(r"\w+", value.casefold()))


def text_column(declared_type, spider_type):
    return any(part in (declared_type or "").upper() for part in TEXT_TYPES) or spider_type == "text"


def indexed_values(connection, table, column):
    query = (f"SELECT DISTINCT {quote(column)} FROM {quote(table)} "
             f"WHERE {quote(column)} IS NOT NULL LIMIT ?")
    values = connection.execute(query, (MAX_DISTINCT_PER_COLUMN + 1,)).fetchall()
    if len(values) > MAX_DISTINCT_PER_COLUMN:
        return [], True
    kept = []
    for (value,) in values:
        if not isinstance(value, str) or not 2 <= len(value) <= MAX_VALUE_LENGTH:
            continue
        key = normalize(value)
        if not key:
            continue
        kept.append({"table": table, "column": column, "value": value, "key": key})
    return kept, False


def build_one(db_id, sqlite_path):
    source = SEMANTICS / f"{db_id}.json"
    if not source.is_file():
        raise FileNotFoundError(f"missing base semantics: {source}")
    base = json.loads(source.read_text())
    if base["dataset"] != db_id:
        raise ValueError(f"semantics database mismatch: {source}")
    # Spider metadata labels some non-unique columns as primary keys. Keep the
    # raw key declaration, but do not copy its unverified row-grain assertion.
    entities = copy.deepcopy(base["entities"])
    entities.pop("sqlite_sequence", None)
    for entity in entities.values():
        entity.pop("grain", None)
    relationships = []
    values = []
    skipped = []
    with sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True) as connection:
        connection.text_factory = lambda raw: raw.decode("utf-8", "replace")
        connection.execute("PRAGMA query_only = 1")
        for table, entity in entities.items():
            declared = {row[1].casefold(): row[2] for row in connection.execute(
                f"PRAGMA table_info({quote(table)})")}
            if not declared:
                raise ValueError(f"table in semantics is missing from SQLite: {table}")
            for column, detail in entity["columns"].items():
                if column.casefold() not in declared:
                    raise ValueError(f"column in semantics is missing from SQLite: {table}.{column}")
                foreign_key = detail.get("foreign_key")
                if foreign_key:
                    relationships.append({"from_table": table, "from_column": column,
                                          "to_table": foreign_key["table"],
                                          "to_column": foreign_key["column"],
                                          "source": "Spider tables.json foreign_keys"})
                if text_column(declared[column.casefold()], detail.get("type")):
                    found, too_many = indexed_values(connection, table, column)
                    values.extend(found)
                    if too_many:
                        skipped.append(f"{table}.{column}")
    values.sort(key=lambda item: (item["key"], item["table"], item["column"], item["value"]))
    relationships.sort(key=lambda item: (item["from_table"], item["from_column"]))
    return {
        "format_version": "1.0",
        "db_id": db_id,
        "source": {
            "schema": "data/semantics_json/<db_id>.json (Spider tables.json and SQLite)",
            "values": "observed distinct strings in the matching Spider SQLite database",
            "questions_or_gold_sql_used": False,
        },
        "status": "machine_derived_needs_domain_review",
        "entities": entities,
        "relationships": relationships,
        "terms": {term: detail for term, detail in base["terms"].items()
                  if detail["maps_to"] in entities},
        "metrics": {name: detail for name, detail in base["metrics"].items()
                    if detail["base_table"] in entities},
        "values": values,
        "value_index_limit_per_column": MAX_DISTINCT_PER_COLUMN,
        "skipped_high_cardinality_columns": skipped,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-id", help="build just one database; default is all 20 Spider dev databases")
    args = parser.parse_args()
    paths = {path.stem: DATABASES / path.stem / f"{path.stem}.sqlite"
             for path in DATAONLY.glob("*.sql")}
    if args.db_id:
        if args.db_id not in paths:
            parser.error(f"database is not in the evaluation set: {args.db_id}")
        paths = {args.db_id: paths[args.db_id]}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for db_id, sqlite_path in sorted(paths.items()):
        catalog = build_one(db_id, sqlite_path)
        path = OUTPUT / f"{db_id}.json"
        path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
        print(f"{db_id}: {len(catalog['entities'])} tables, "
              f"{len(catalog['relationships'])} relationships, "
              f"{len(catalog['values'])} indexed values -> {path}")


if __name__ == "__main__":
    main()
