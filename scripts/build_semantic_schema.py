"""
Build an accuracy-oriented "semantic layer" schema string per database, to use
in place of the plain schema_text prompt in run_eval.py.

Design choice (accuracy over polish — see conversation record / team-lead ask):
Spider ships no real business documentation, so anything hand-written as
business-meaning prose would be an authored guess, not a fact, and could
mislead a model as easily as help it. Instead, everything added here is
derived directly from tables.json + the real sqlite data:

  1. Real sample values for low-cardinality TEXT columns, pulled straight
     from the database. This targets a concrete failure mode we saw in
     practice (a model producing 'Bachelors' where gold used 'Bachelor') —
     showing the model the actual strings it needs to match.
  2. Auto-detected schema quirks that are objectively true, not guessed:
       - FK whose declared type differs from the column it references
       - FK that targets a column which is NOT that table's primary key
         (Spider schemas are sometimes joined by a non-PK "name" column
         instead of the numeric id — a real, verifiable trap.)

Annotations are placed inline as SQL comments next to each column (same
CREATE-TABLE style as build_schema_text in prepare_dataset.py), since
research on text-to-SQL prompting finds inline annotations help smaller
models more than a separate documentation block does.

Usage:
    python3 scripts/build_semantic_schema.py <db_id> [<db_id> ...]
    python3 scripts/build_semantic_schema.py --all-eval-sample
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path("/home/lenovo/Documents/model_study")
DATA = ROOT / "data"
SPIDER = DATA / "spider_data"
PATTERNS_DIR = DATA / "question_patterns"

# Two variants, because only PART of this layer carries leakage risk:
#   full      = everything, including usage patterns mined from dev's gold SQL.
#               Valid ONLY against the invented eval set.
#   dataonly  = readable names, sample values, numeric ranges, row counts and
#               FK quirks. All derived from the DATABASE CONTENTS, never from
#               questions or answers — so it is leak-free and valid against the
#               real Spider dev questions.
OUT_DIR_FULL = DATA / "semantic_layer"
OUT_DIR_DATAONLY = DATA / "semantic_layer_dataonly"

MAX_DISTINCT_TO_SHOW = 12  # only show sample values if column has <= this many distinct values
SAMPLE_LIMIT = 12
MAX_JOINS_SHOWN = 6
MAX_AGGS_SHOWN = 6
MAX_NUMERIC_RANGE_COLS = 40  # guard against pathological wide tables

# Phrase -> SQL construct hints. Generic SQL idioms, not per-db facts, so these
# carry no leakage risk; they're included only when this db's own question set
# actually exercises the construct (see build_usage_notes).
PHRASE_HINTS = [
    ("COUNT", "'how many' / 'number of' -> COUNT"),
    ("AVG", "'average' / 'mean' -> AVG"),
    ("GROUP BY", "'for each' / 'per <thing>' / 'by <thing>' -> GROUP BY"),
    ("ORDER BY ... DESC", "'most' / 'highest' / 'largest' / 'top' -> ORDER BY ... DESC"),
    ("LIMIT 1", "'the single most/least ...' -> ORDER BY ... LIMIT 1"),
    ("negation (NOT IN / EXCEPT)", "'never' / 'without any' / 'that do not' -> NOT IN / EXCEPT"),
    ("INTERSECT", "'both X and Y' -> INTERSECT"),
    ("subquery", "'more than the average' / comparisons to an aggregate -> subquery"),
]


def humanize(col_name: str) -> str:
    """'Net_Worth_Millions' -> 'net worth millions'. Returns '' if it adds nothing.

    Deliberately mechanical: this restates the column's own name in readable
    words, it does NOT invent business meaning (Spider ships no documentation
    to source that from).
    """
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", col_name)
    s = s.replace("_", " ").strip()
    s = re.sub(r"\s+", " ", s).lower()
    if s.replace(" ", "") == col_name.lower().replace("_", ""):
        if " " not in s:
            return ""  # single word, same as the column name — no value added
    return s


def load_tables():
    tables_path = next(SPIDER.rglob("tables.json"))
    return {t["db_id"]: t for t in json.loads(tables_path.read_text())}


def sqlite_path_for(db_id):
    db_dirs = [p for p in SPIDER.rglob("database") if p.is_dir()]
    return db_dirs[0] / db_id / f"{db_id}.sqlite"


def get_distinct_values(conn, table, column):
    try:
        cur = conn.execute(f'SELECT COUNT(DISTINCT "{column}") FROM "{table}"')
        n_distinct = cur.fetchone()[0]
        if n_distinct == 0 or n_distinct > MAX_DISTINCT_TO_SHOW:
            return None
        cur = conn.execute(
            f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL LIMIT ?',
            (SAMPLE_LIMIT,),
        )
        # Empty strings are not information — advertising "values: ''" is noise.
        vals = [row[0] for row in cur.fetchall()
                if not (isinstance(row[0], str) and not row[0].strip())]
        return vals or None
    except sqlite3.Error:
        return None


def is_identifier_col(name: str) -> bool:
    """Identifier-ish columns whose numeric range is noise, not information.

    'Document_ID range: 3 to 385906526' tells a model nothing useful and eats
    prompt space; ranges only help for genuine quantities.
    """
    low = name.lower()
    return low == "id" or low.endswith("_id") or low.endswith("id") and len(low) <= 6


def get_numeric_range(conn, table, column):
    """min/max for a numeric column — grounds threshold/comparison questions."""
    try:
        cur = conn.execute(
            f'SELECT MIN("{column}"), MAX("{column}") FROM "{table}" '
            f'WHERE "{column}" IS NOT NULL'
        )
        lo, hi = cur.fetchone()
        if lo is None or hi is None or lo == hi:
            return None
        # SQLite hands back floats for integer-valued columns; don't render 1940.0
        def tidy(v):
            if isinstance(v, float) and v.is_integer():
                return int(v)
            return v
        return tidy(lo), tidy(hi)
    except sqlite3.Error:
        return None


def get_row_count(conn, table):
    try:
        return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    except sqlite3.Error:
        return None


def build_usage_notes(db_id):
    """Trailing section built from mine_question_patterns.py output.

    Everything here is mined from THIS database's real dev.json questions +
    gold SQL. That is why models prompted with it must not be graded on those
    same dev questions — see the leakage note in mine_question_patterns.py.
    """
    path = PATTERNS_DIR / f"{db_id}.json"
    if not path.exists():
        return ""
    p = json.loads(path.read_text())
    if not p.get("n_questions"):
        return ""

    lines = [
        "",
        "-- ============================================================",
        f"-- USAGE PATTERNS for {db_id}",
        f"-- Mined from {p['n_questions']} real analyst questions against this database.",
        "-- Heuristic (regex-derived, not a SQL parser) — treat as guidance, not rules.",
        "-- ============================================================",
    ]

    joins = p.get("join_pairs", [])[:MAX_JOINS_SHOWN]
    if joins:
        lines.append(f"-- Most common join paths ({p['n_questions_with_join']} of "
                     f"{p['n_questions']} questions join at least two tables):")
        for j in joins:
            lines.append(f"--   {j['n']:>3} questions:  {j['left']} = {j['right']}")

    aggs = [a for a in p.get("agg_usage", []) if a["target"] != "*"][:MAX_AGGS_SHOWN]
    star = next((a for a in p.get("agg_usage", []) if a["target"] == "*"), None)
    if aggs or star:
        lines.append("-- Metrics this database is usually asked for:")
        if star:
            lines.append(f"--   {star['n']:>3} questions:  COUNT(*)  (plain row counts are the single most common ask)")
        for a in aggs:
            lines.append(f"--   {a['n']:>3} questions:  {a['fn']}({a['target']})")

    exercised = set()
    for counter in p.get("question_openers", {}).values():
        exercised.update(counter.keys())
    hints = [text for key, text in PHRASE_HINTS if key in exercised]
    if hints:
        lines.append("-- Phrasing -> SQL constructs seen in this database's questions:")
        for h in hints:
            lines.append(f"--   {h}")

    return "\n".join(lines)


def build_semantic_schema(db_id, entry, conn, include_usage=True):
    table_names = entry["table_names_original"]
    col_names = entry["column_names_original"]
    col_types = entry["column_types"]
    pk = set(entry.get("primary_keys", []))
    fks = entry.get("foreign_keys", [])

    # col_idx -> (target_table_idx, target_col_idx) for FK source columns
    fk_by_src = {src: tgt for src, tgt in fks}

    # table_idx -> set of col_idx that are that table's primary key
    pk_by_table = {}
    for col_idx in pk:
        t_idx, _ = col_names[col_idx]
        pk_by_table.setdefault(t_idx, set()).add(col_idx)

    cols_by_table = {i: [] for i in range(len(table_names))}
    for col_idx, (t_idx, c_name) in enumerate(col_names):
        if t_idx == -1:
            continue
        cols_by_table[t_idx].append((col_idx, c_name, col_types[col_idx]))

    # The header must describe what is ACTUALLY in this variant — the dataonly
    # build has no usage-patterns section, and promising one the model never
    # sees is worse than saying nothing.
    lines = [
        f"-- db_id: {db_id}",
        "-- Schema annotated with readable column names, real sample values and",
        "-- value ranges taken from the data, and auto-detected join quirks.",
    ]
    if include_usage:
        lines.append("-- Usage patterns mined from real questions follow at the bottom.")

    for t_idx, tname in enumerate(table_names):
        n_rows = get_row_count(conn, tname) if conn is not None else None
        header = f"CREATE TABLE {tname} ("
        if n_rows is not None:
            header += f"  -- {n_rows} rows"
        lines.append(header)
        col_lines = []
        for col_idx, cname, ctype in cols_by_table[t_idx]:
            parts = [f"{cname} {ctype.upper()}"]
            if col_idx in pk:
                parts.append("PRIMARY KEY")
            comment_bits = []

            meaning = humanize(cname)
            if meaning:
                comment_bits.append(meaning)

            if col_idx in fk_by_src:
                tgt_idx = fk_by_src[col_idx]
                tgt_t_idx, tgt_c_name = col_names[tgt_idx]
                tgt_table = table_names[tgt_t_idx]
                tgt_type = col_types[tgt_idx]
                comment_bits.append(f"FK -> {tgt_table}.{tgt_c_name}")

                if ctype != tgt_type:
                    comment_bits.append(
                        f"TYPE MISMATCH: this col is {ctype.upper()}, target is {tgt_type.upper()} (no CAST needed in SQLite, but be aware)"
                    )
                tgt_pk_set = pk_by_table.get(tgt_t_idx, set())
                if tgt_idx not in tgt_pk_set:
                    comment_bits.append(
                        f"JOINS BY NON-PRIMARY-KEY COLUMN (target is not {tgt_table}'s own primary key)"
                    )

            if conn is not None and ctype.lower() == "text":
                vals = get_distinct_values(conn, tname, cname)
                if vals:
                    shown = ", ".join(repr(v) for v in vals)
                    comment_bits.append(f"values: {shown}")
            elif (conn is not None and ctype.lower() == "number"
                  and col_idx not in pk and not is_identifier_col(cname)):
                rng = get_numeric_range(conn, tname, cname)
                if rng:
                    comment_bits.append(f"range: {rng[0]} to {rng[1]}")

            line = "  " + " ".join(parts)
            col_lines.append((line, comment_bits))

        rendered = []
        for i, (line, comment_bits) in enumerate(col_lines):
            is_last = i == len(col_lines) - 1
            if not is_last:
                line += ","
            if comment_bits:
                line += "  -- " + " | ".join(comment_bits)
            rendered.append(line)
        lines.append("\n".join(rendered))
        lines.append(");")

    if include_usage:
        usage = build_usage_notes(db_id)
        if usage:
            lines.append(usage)

    return "\n".join(lines)


def main():
    args = [a for a in sys.argv[1:]]
    tables = load_tables()

    if "--all-eval-sample" in args:
        args.remove("--all-eval-sample")
        eval_sample = json.loads((DATA / "eval_sample.json").read_text())
        db_ids = sorted(set(e["db_id"] for e in eval_sample))
    elif args:
        db_ids = args
    else:
        print("usage: build_semantic_schema.py <db_id> [<db_id> ...] | --all-eval-sample")
        sys.exit(1)

    OUT_DIR_FULL.mkdir(exist_ok=True)
    OUT_DIR_DATAONLY.mkdir(exist_ok=True)
    for db_id in db_ids:
        if db_id not in tables:
            print(f"skip {db_id}: not found in tables.json")
            continue
        sqlite_path = sqlite_path_for(db_id)
        conn = None
        if sqlite_path.exists():
            conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True, timeout=5)
        else:
            print(f"warn {db_id}: sqlite file not found, skipping sample values")

        full = build_semantic_schema(db_id, tables[db_id], conn, include_usage=True)
        dataonly = build_semantic_schema(db_id, tables[db_id], conn, include_usage=False)
        if conn:
            conn.close()

        (OUT_DIR_FULL / f"{db_id}.sql").write_text(full)
        (OUT_DIR_DATAONLY / f"{db_id}.sql").write_text(dataonly)
        print(f"{db_id:32} full={len(full):6} chars   dataonly={len(dataonly):6} chars")


if __name__ == "__main__":
    main()
