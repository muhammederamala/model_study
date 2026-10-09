"""Retrieve source-grounded context for a question without calling a model.

Usage:
  python3 scripts/ground_question.py --id 153
  python3 scripts/ground_question.py --db-id battle_death --question "Which battle lost Lettice?"

This component also feeds the separate grounded Qwen evaluation runner. It does
not generate SQL. The returned matches are candidates, not business facts.
"""

import argparse
import json
import re
import time
from collections import deque
from functools import lru_cache
from pathlib import Path

from build_semantic_catalog import ROOT, normalize


CATALOG_DIR = ROOT / "data/semantic_catalog"
REVIEWED = ROOT / "data/reviewed_semantics.md"
DATASET = ROOT / "data/eval_sample.json"
VALUE_STOPWORDS = {"and", "are", "average", "both", "car", "cars", "city",
                   "code", "country", "date", "day", "each", "first", "for",
                   "from", "have", "highest", "into", "last", "list", "lost",
                   "model", "models", "month", "most", "name", "names", "not",
                   "number", "one", "only", "other", "player", "players", "show",
                   "state", "than", "that", "the", "their", "there", "these",
                   "this", "those", "total", "type", "which", "with", "won",
                   "year"}
GENERIC_COLUMNS = {"id", "name", "date", "type", "code", "description", "status"}


def phrase_present(phrase, text):
    return bool(phrase) and f" {phrase} " in f" {text} "


def stemmed(value):
    words = normalize(value).split()
    stems = []
    for word in words:
        if len(word) > 4 and word.endswith("ies"):
            word = word[:-3] + "y"
        elif len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        stems.append(word)
    return " ".join(stems)


def label_score(labels, question):
    stemmed_question = stemmed(question)
    scores = [10 + len(normalize(label).split()) * 3
              for label in labels if phrase_present(stemmed(label), stemmed_question)]
    return max(scores, default=0)


@lru_cache(maxsize=32)
def load_catalog(db_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", db_id):
        raise ValueError("invalid db_id")
    path = CATALOG_DIR / f"{db_id}.json"
    catalog = json.loads(path.read_text())
    if catalog["db_id"] != db_id:
        raise ValueError(f"catalog ID mismatch: {path}")
    return catalog


@lru_cache(maxsize=32)
def load_reviewed_notes(db_id):
    """Select this database's manually reviewed section, never another DB's."""
    heading = f"## {db_id}\n"
    content = REVIEWED.read_text()
    start = content.find(heading)
    if start < 0:
        raise ValueError(f"no reviewed semantics section for {db_id}")
    body = content[start + len(heading):].split("\n## ", 1)[0].strip()
    if not body:
        raise ValueError(f"empty reviewed semantics section for {db_id}")
    return body


def shortest_path(start, goal, relationships):
    if start == goal:
        return []
    graph = {}
    for index, edge in enumerate(relationships):
        graph.setdefault(edge["from_table"], []).append((edge["to_table"], index))
        graph.setdefault(edge["to_table"], []).append((edge["from_table"], index))
    pending = deque([(start, [])])
    seen = {start}
    while pending:
        table, path = pending.popleft()
        for neighbor, index in graph.get(table, []):
            if neighbor in seen:
                continue
            next_path = path + [index]
            if neighbor == goal:
                return next_path
            seen.add(neighbor)
            pending.append((neighbor, next_path))
    return []


def ground(question, catalog, max_values=10, max_columns=10, max_joins=8):
    question_key = normalize(question)
    quoted = [normalize(value) for value in re.findall(r"['\"“”]([^'\"“”]+)['\"“”]", question)]
    value_hits = []
    for item in catalog["values"]:
        key = item["key"]
        if not phrase_present(key, question_key):
            continue
        if len(key) < 3 and key not in quoted:
            continue
        if key in VALUE_STOPWORDS and key not in quoted:
            continue
        score = 20 + min(len(key), 40) + 8 * (len(key.split()) - 1)
        if key in quoted:
            score += 100
        value_hits.append({"table": item["table"], "column": item["column"],
                           "value": item["value"], "score": score,
                           "source": "observed SQLite value"})
    value_hits.sort(key=lambda hit: (-hit["score"], hit["table"], hit["column"], hit["value"]))
    value_hits = value_hits[:max_values]

    table_hits = []
    column_hits = []
    for table, entity in catalog["entities"].items():
        table_score = label_score((table, entity.get("source_label", "")), question)
        if table_score:
            table_hits.append({"table": table, "score": table_score,
                               "source": "Spider schema label"})
        for column, detail in entity["columns"].items():
            labels = (column, detail.get("source_label", ""))
            score = label_score(labels, question)
            if score and (stemmed(column) not in GENERIC_COLUMNS or table_score):
                column_hits.append({"table": table, "column": column,
                                    "score": score + (5 if table_score else 0),
                                    "source": "Spider schema label"})
    table_hits.sort(key=lambda hit: (-hit["score"], hit["table"]))
    column_hits.sort(key=lambda hit: (-hit["score"], hit["table"], hit["column"]))
    table_hits = table_hits[:6]
    column_hits = column_hits[:max_columns]

    anchors = {hit["table"] for hit in table_hits[:4]}
    anchors.update(hit["table"] for hit in value_hits[:max_values])
    anchors.update(hit["table"] for hit in column_hits[:4])
    relationships = catalog["relationships"]
    edge_ids = set()
    for left in sorted(anchors):
        for right in sorted(anchors):
            if left < right:
                edge_ids.update(shortest_path(left, right, relationships))
    # A shortest path can choose one of several FKs between the same tables.
    # Keep all declared alternatives so 'depart from' is not forced to use a
    # destination-airport join, or 'winner' to use a loser-player join.
    connected_pairs = {frozenset((relationships[index]["from_table"],
                                  relationships[index]["to_table"])) for index in edge_ids}
    edge_ids.update(index for index, edge in enumerate(relationships)
                    if frozenset((edge["from_table"], edge["to_table"])) in connected_pairs)
    joins = [relationships[index] for index in sorted(edge_ids)[:max_joins]]
    return {"db_id": catalog["db_id"], "question": question,
            "table_matches": table_hits, "column_matches": column_hits,
            "value_matches": value_hits, "join_paths": joins,
            "reviewed_notes": load_reviewed_notes(catalog["db_id"]),
            "status": "candidate context; labels and values are not verified business definitions"}


def format_context(result):
    lines = ["Question-specific database context (candidates; verify against the schema):"]
    lines.append("Reviewed structural notes for this database (from schema and SQLite rows):")
    lines.append(result["reviewed_notes"])
    if result["value_matches"]:
        lines.append("Observed values matching the question:")
        for hit in result["value_matches"]:
            value = hit["value"]
            whitespace_note = " (stored with surrounding whitespace)" if value != value.strip() else ""
            lines.append(f"- {hit['table']}.{hit['column']} contains "
                         f"{json.dumps(value, ensure_ascii=False)}{whitespace_note}")
    if result["table_matches"]:
        lines.append("Tables matching the question wording:")
        for hit in result["table_matches"][:4]:
            lines.append(f"- {hit['table']}")
    if result["column_matches"]:
        lines.append("Columns matching the question wording:")
        for hit in result["column_matches"][:8]:
            lines.append(f"- {hit['table']}.{hit['column']}")
    if result["join_paths"]:
        lines.append("Declared FK paths (check stored values before using SQL equality):")
        for edge in result["join_paths"]:
            lines.append(f"- {edge['from_table']}.{edge['from_column']} -> "
                         f"{edge['to_table']}.{edge['to_column']}")
    if not any(result[key] for key in ("value_matches", "table_matches", "column_matches")):
        lines.append("No strong lexical or observed-value match; use the full schema.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--id", type=int, help="preview a Spider dev question by ID")
    source.add_argument("--question", help="question text; requires --db-id")
    parser.add_argument("--db-id", help="database ID for --question")
    parser.add_argument("--json", action="store_true", help="print ranked matches instead of prompt text")
    args = parser.parse_args()
    if args.id is not None:
        examples = json.loads(DATASET.read_text())
        example = next((ex for ex in examples if ex["id"] == args.id), None)
        if example is None:
            parser.error(f"unknown evaluation ID: {args.id}")
        db_id, question = example["db_id"], example["question"]
    else:
        if not args.db_id:
            parser.error("--db-id is required with --question")
        db_id, question = args.db_id, args.question
    started = time.perf_counter()
    result = ground(question, load_catalog(db_id))
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else format_context(result))
    print(f"\nRetrieval time: {(time.perf_counter() - started) * 1000:.1f} ms")


if __name__ == "__main__":
    main()
