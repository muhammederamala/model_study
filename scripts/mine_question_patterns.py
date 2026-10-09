"""
Mine per-database usage patterns from the REAL Spider dev questions + gold SQL,
to feed the semantic layer built by build_semantic_schema.py.

WHY THIS IS SAFE (leakage note, 2026-09-29):
  These patterns are mined from dev.json's gold SQL — i.e. from the ANSWERS to
  the real Spider questions. That means any model prompted with these patterns
  must NOT be graded on those same dev questions, or the number is inflated and
  meaningless (the prompt would encode the shape of the answer).
  The agreed design is: mine dev freely HERE, and evaluate on the separately
  generated invented dataset (data/invented_eval.json) instead. See
  levers/MANIFEST.md and CLAUDE.md for the full reasoning.

WHAT IT EXTRACTS (all heuristic/regex — not a real SQL parser, see caveats):
  - join_pairs:      resolved table.column = table.column, with frequency
  - column_usage:    per column, how often it appears in WHERE / GROUP BY /
                     ORDER BY / SELECT, and under which aggregate functions
  - agg_patterns:    which aggregate functions are applied to which columns
  - phrasing:        common natural-language openers in this db's questions and
                     the SQL constructs that co-occur with them

CAVEATS: alias resolution handles the common `FROM t AS T1 JOIN u AS T2` form
Spider uses, but not subquery-scoped aliases or correlated subqueries reliably.
Counts are indicative, not exact. Output is labelled as heuristic wherever it
reaches the prompt.

Usage: python3 scripts/mine_question_patterns.py
Writes data/question_patterns/<db_id>.json
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/home/lenovo/Documents/model_study")
DATA = ROOT / "data"
SPIDER = DATA / "spider_data"
OUT_DIR = DATA / "question_patterns"

AGG_FNS = ["count", "sum", "avg", "min", "max"]

ALIAS_RE = re.compile(r"\b(?:FROM|JOIN)\s+([A-Za-z_]\w*)\s+AS\s+([A-Za-z_]\w*)", re.IGNORECASE)
EQ_JOIN_RE = re.compile(r"([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\.([A-Za-z_]\w*)")
AGG_RE = re.compile(r"\b(count|sum|avg|min|max)\s*\(\s*(?:distinct\s+)?([A-Za-z_][\w.]*|\*)\s*\)", re.IGNORECASE)


def resolve_aliases(sql):
    """alias -> real table name, from `FROM t AS T1` / `JOIN u AS T2` forms."""
    return {alias.lower(): table.lower() for table, alias in ALIAS_RE.findall(sql)}


def qualify(alias_map, prefix, col):
    """Turn T1.foo into realtable.foo where possible."""
    p = prefix.lower()
    return f"{alias_map.get(p, p)}.{col.lower()}"


def clause_of(sql_lower, col):
    """Which clauses mention this bare column name. Heuristic: split on keywords."""
    found = set()
    # crude clause segmentation — good enough for Spider's mostly-flat queries
    segments = {
        "where": re.split(r"\bwhere\b", sql_lower)[1:],
        "group by": re.split(r"\bgroup by\b", sql_lower)[1:],
        "order by": re.split(r"\border by\b", sql_lower)[1:],
        "having": re.split(r"\bhaving\b", sql_lower)[1:],
    }
    for clause, parts in segments.items():
        for part in parts:
            # stop at the next major keyword so clauses don't bleed into each other
            part = re.split(r"\b(?:group by|order by|having|limit|union|intersect|except)\b", part)[0]
            if re.search(rf"\b{re.escape(col)}\b", part):
                found.add(clause)
    return found


def mine_db(db_id, rows, table_cols):
    """rows: list of (question, gold_sql). table_cols: {table_lower: [col_lower,...]}"""
    join_pairs = Counter()
    agg_usage = Counter()          # (fn, column) -> n
    clause_usage = defaultdict(Counter)  # column -> Counter(clause -> n)
    opener_constructs = defaultdict(Counter)  # opener -> Counter(construct -> n)
    n_with_join = 0

    all_cols = {c for cols in table_cols.values() for c in cols}

    for question, sql in rows:
        sql_lower = sql.lower()
        alias_map = resolve_aliases(sql)

        # --- joins ---
        pairs_here = set()
        for a_pfx, a_col, b_pfx, b_col in EQ_JOIN_RE.findall(sql):
            left = qualify(alias_map, a_pfx, a_col)
            right = qualify(alias_map, b_pfx, b_col)
            if left == right:
                continue
            pairs_here.add(tuple(sorted([left, right])))
        if pairs_here:
            n_with_join += 1
        for p in pairs_here:
            join_pairs[p] += 1

        # --- aggregates ---
        for fn, target in AGG_RE.findall(sql):
            t = target.lower()
            if "." in t:
                pfx, col = t.split(".", 1)
                t = qualify(alias_map, pfx, col)
            agg_usage[(fn.lower(), t)] += 1

        # --- clause usage per column ---
        for col in all_cols:
            for clause in clause_of(sql_lower, col):
                clause_usage[col][clause] += 1

        # --- question phrasing -> construct ---
        opener = " ".join(question.strip().lower().split()[:3])
        constructs = []
        if re.search(r"\bgroup by\b", sql_lower):
            constructs.append("GROUP BY")
        if re.search(r"\border by\b.*\bdesc\b", sql_lower):
            constructs.append("ORDER BY ... DESC")
        if re.search(r"\blimit\s+1\b", sql_lower):
            constructs.append("LIMIT 1")
        if re.search(r"\bcount\s*\(", sql_lower):
            constructs.append("COUNT")
        if re.search(r"\bavg\s*\(", sql_lower):
            constructs.append("AVG")
        if re.search(r"\bnot in\b|\bexcept\b", sql_lower):
            constructs.append("negation (NOT IN / EXCEPT)")
        if re.search(r"\bintersect\b", sql_lower):
            constructs.append("INTERSECT")
        if sql_lower.count("select") > 1:
            constructs.append("subquery")
        for c in constructs:
            opener_constructs[opener][c] += 1

    return {
        "db_id": db_id,
        "n_questions": len(rows),
        "n_questions_with_join": n_with_join,
        "join_pairs": [
            {"left": a, "right": b, "n": n}
            for (a, b), n in join_pairs.most_common()
        ],
        "agg_usage": [
            {"fn": fn.upper(), "target": target, "n": n}
            for (fn, target), n in agg_usage.most_common()
        ],
        "column_clause_usage": {
            col: dict(counter.most_common())
            for col, counter in sorted(clause_usage.items())
            if counter
        },
        "question_openers": {
            opener: dict(counter.most_common())
            for opener, counter in sorted(opener_constructs.items(), key=lambda x: -sum(x[1].values()))
            if sum(counter.values()) >= 2
        },
    }


def main():
    dev = json.loads((SPIDER / "dev.json").read_text())
    tables = {t["db_id"]: t for t in json.loads((SPIDER / "tables.json").read_text())}

    by_db = defaultdict(list)
    for ex in dev:
        by_db[ex["db_id"]].append((ex["question"], ex["query"]))

    OUT_DIR.mkdir(exist_ok=True)
    for db_id, rows in sorted(by_db.items()):
        entry = tables[db_id]
        table_names = [t.lower() for t in entry["table_names_original"]]
        table_cols = defaultdict(list)
        for t_idx, c_name in entry["column_names_original"]:
            if t_idx == -1:
                continue
            table_cols[table_names[t_idx]].append(c_name.lower())

        patterns = mine_db(db_id, rows, table_cols)
        out = OUT_DIR / f"{db_id}.json"
        out.write_text(json.dumps(patterns, indent=2))
        print(f"{db_id:32} n={patterns['n_questions']:4}  joins={len(patterns['join_pairs']):3}  "
              f"aggs={len(patterns['agg_usage']):3}  openers={len(patterns['question_openers']):3}  -> {out.name}")


if __name__ == "__main__":
    main()
