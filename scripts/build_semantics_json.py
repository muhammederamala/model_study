"""Build standalone, source-grounded semantics JSON for every Spider schema.

This does not change evaluation prompts. No questions, gold SQL, or inferred
business definitions are used. Run: python3 scripts/build_semantics_json.py
"""

import json
import sqlite3
from contextlib import closing
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "data/spider_data/tables.json"
DATABASES = ROOT / "data/spider_data/database"
OUTPUT = ROOT / "data/semantics_json"
MAX_VALUES = 12


def quote(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def observed_values(connection, table, column):
    sql = (f"SELECT DISTINCT {quote(column)} FROM {quote(table)} "
           f"WHERE {quote(column)} IS NOT NULL LIMIT {MAX_VALUES + 1}")
    try:
        values = [row[0] for row in connection.execute(sql)]
    except sqlite3.Error:
        return None
    if len(values) > MAX_VALUES:
        return None
    values = [value for value in values if not isinstance(value, str) or value.strip()]
    return values or None


def row_count(connection, table):
    try:
        return connection.execute(f"SELECT COUNT(*) FROM {quote(table)}").fetchone()[0]
    except sqlite3.Error:
        return None


def make_document(entry, connection):
    names = entry["table_names_original"]
    labels = entry["table_names"]
    columns = entry["column_names_original"]
    column_labels = entry["column_names"]
    types = entry["column_types"]
    primary_keys = set(entry.get("primary_keys", []))
    foreign_keys = {source: target for source, target in entry.get("foreign_keys", [])}
    entities = {}
    terms = {}
    metrics = {}

    for table_index, table in enumerate(names):
        table_columns = {}
        key_columns = []
        for index, (owner, column) in enumerate(columns):
            if owner != table_index:
                continue
            label = column_labels[index][1]
            detail = {"type": types[index], "source_label": label}
            if index in primary_keys:
                detail["primary_key"] = True
                key_columns.append(column)
            if index in foreign_keys:
                target_table_index, target_column = columns[foreign_keys[index]]
                detail["foreign_key"] = {
                    "table": names[target_table_index], "column": target_column
                }
            if connection is not None and types[index].lower() == "text":
                values = observed_values(connection, table, column)
                if values is not None:
                    detail["observed_values"] = values
            table_columns[column] = detail

        entity = {
            "source_label": labels[table_index],
            "meaning": f"Table labeled '{labels[table_index]}' in Spider schema metadata; business meaning is unconfirmed.",
            "grain": ("one row identified by the schema's primary key "
                      + ", ".join(key_columns)) if key_columns else "one table row; no primary key is declared in Spider metadata",
            "primary_key_columns": key_columns,
            "columns": table_columns,
        }
        if connection is not None:
            count = row_count(connection, table)
            if count is not None:
                entity["observed_row_count"] = count
        entities[table] = entity
        metrics[f"{table}__row_count"] = {
            "meaning": f"Number of rows in {table}.",
            "base_table": table,
            "calculation": "COUNT(*)",
            "status": "structural metric; business interpretation unconfirmed",
        }
        if labels[table_index].casefold() != table.casefold():
            terms[labels[table_index]] = {"maps_to": table, "source": "Spider normalized table name"}

    return {
        "format_version": "1.0",
        "kind": "text_to_sql_semantics",
        "schema_file": "data/spider_data/tables.json",
        "dataset": entry["db_id"],
        "status": "machine_derived_needs_domain_review",
        "important": ("Table and column labels, types, keys, and foreign keys come from Spider tables.json. "
                      "Observed values and row counts come from its SQLite database. "
                      "Labels are hints, not confirmed business definitions. No business metrics or assumptions have been invented."),
        "assumptions_to_confirm": [],
        "entities": entities,
        "terms": terms,
        "metrics": metrics,
        "query_rules": [
            "Use only tables and columns declared in this schema.",
            "Use foreign-key joins declared in the schema when applicable; do not invent relationships.",
            "Check the row grain before aggregating across one-to-many joins to avoid duplicate counts or sums.",
            "Observed values are examples from the supplied SQLite database, not an exhaustive value list unless the source data remains unchanged.",
            "Do not infer business metrics, units, time zones, or status meanings from column names alone; clarify when necessary."
        ],
        "example_interpretations": [],
    }


def main():
    entries = json.loads(TABLES.read_text())
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        db_id = entry["db_id"]
        db_path = DATABASES / db_id / f"{db_id}.sqlite"
        if not db_path.is_file():
            raise FileNotFoundError(db_path)
        with closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)) as connection:
            document = make_document(entry, connection)
        (OUTPUT / f"{db_id}.json").write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        )
    print(f"Wrote {len(entries)} semantics files to {OUTPUT}")


if __name__ == "__main__":
    main()
