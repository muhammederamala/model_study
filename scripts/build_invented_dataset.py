"""
Generate our own text-to-SQL evaluation set against the same 20 Spider dev
databases — questions + gold SQL that are NOT part of Spider.

WHY THIS EXISTS (2026-09-29):
  The semantic layer (data/semantic_layer/*.sql) is built partly from patterns
  mined out of Spider dev's gold SQL. Grading a model on those same dev
  questions while feeding it those mined patterns is leakage — the prompt would
  encode the shape of the answers. So: mine dev freely, but evaluate HERE, on
  questions whose answers never fed the prompt.

HOW IT WORKS:
  SQL is generated from templates instantiated against each database's real
  schema, real foreign-key graph, and real column values, then verified by
  execution. That makes the gold SQL correct by construction — the alternative
  (hand-authoring 500 queries) would make my own SQL bugs the ground truth.

KNOWN LIMITATION — read before trusting the numbers:
  Templated questions are less linguistically varied than Spider's
  human-written ones. Multiple surface phrasings per template soften this, but
  accuracy here may not fully transfer to messy real-world phrasing. Treat this
  as a controlled measurement of SQL-construction ability, not a proxy for
  natural-language robustness. Also: a question being answerable and its SQL
  being *the* right reading of the English is not machine-verifiable — spot
  check a sample by hand (see results CSVs / levers docs).

Usage: python3 scripts/build_invented_dataset.py [total_n]
Writes data/invented_eval.json (same record shape as data/eval_sample.json, so
run_eval.py can consume either).
"""
import json
import random
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from prepare_dataset import sql_complexity_bucket, build_schema_text  # noqa: E402

ROOT = Path("/home/lenovo/Documents/model_study")
DATA = ROOT / "data"
SPIDER = DATA / "spider_data"
OUT_PATH = DATA / "invented_eval.json"

SEED = 1234
TARGET_TOTAL = 500
# Deliberately skewed toward the weak spot rather than mirroring dev's natural
# ~48/35/17 split, which would leave only ~85 complex — too few to tell a real
# improvement from noise.
TARGET_MIX = {"simple": 150, "moderate": 175, "complex": 175}


def q(ident: str) -> str:
    """Quote an identifier — Spider has column names with spaces and symbols."""
    return '"' + ident.replace('"', '""') + '"'


def lit(v):
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


class DbInfo:
    def __init__(self, db_id, entry, conn):
        self.db_id = db_id
        self.conn = conn
        self.tables = entry["table_names_original"]
        self.col_names = entry["column_names_original"]
        self.col_types = entry["column_types"]
        self.pk = set(entry.get("primary_keys", []))
        self.fks = entry.get("foreign_keys", [])

        self.cols_by_table = defaultdict(list)  # t_idx -> [(col_idx, name, type)]
        for ci, (ti, cname) in enumerate(self.col_names):
            if ti == -1:
                continue
            self.cols_by_table[ti].append((ci, cname, self.col_types[ci]))

        self.row_counts = {}
        for ti, tname in enumerate(self.tables):
            try:
                self.row_counts[ti] = conn.execute(f"SELECT COUNT(*) FROM {q(tname)}").fetchone()[0]
            except sqlite3.Error:
                self.row_counts[ti] = 0

    def text_cols(self, ti):
        return [(ci, n) for ci, n, t in self.cols_by_table[ti]
                if t.lower() == "text" and ci not in self.pk]

    def number_cols(self, ti):
        """Numeric columns worth aggregating.

        Excludes identifiers: SUM/AVG of an ID column is arithmetically valid
        but semantically nonsense ('average document id greater than 7064552'),
        which makes for a bad question no matter how correct the SQL is.
        """
        fk_srcs = {src for src, _ in self.fks}
        out = []
        for ci, n, t in self.cols_by_table[ti]:
            if t.lower() != "number" or ci in self.pk or ci in fk_srcs:
                continue
            low = n.lower()
            if low == "id" or low.endswith("_id") or low.endswith("id") and len(low) <= 6:
                continue
            if low.endswith("code") or low.endswith("_no") or low.endswith("number") and "phone" in low:
                continue
            out.append((ci, n))
        return out

    def group_cols(self, ti):
        """Text columns that make a meaningful GROUP BY.

        Requires at least ~2 rows per group on average — grouping by a column
        that is unique per row produces a degenerate 'group' of one, which is
        a pointless question ('for each museum name, the average staff count'
        where every name is distinct).
        """
        n_rows = self.row_counts.get(ti, 0)
        out = []
        for ci, cname in self.text_cols(ti):
            dc = self.distinct_count(ti, cname)
            if 2 <= dc <= 12 and n_rows >= dc * 2:
                out.append((ci, cname))
        return out

    def label_col(self, ti):
        """Best 'human-readable name' column for a table, if any."""
        cands = self.text_cols(ti)
        if not cands:
            return None
        for ci, n in cands:
            if "name" in n.lower() or "title" in n.lower():
                return (ci, n)
        return cands[0]

    def distinct_count(self, ti, cname):
        try:
            return self.conn.execute(
                f"SELECT COUNT(DISTINCT {q(cname)}) FROM {q(self.tables[ti])}"
            ).fetchone()[0]
        except sqlite3.Error:
            return 0

    def sample_value(self, ti, cname, rng):
        try:
            rows = self.conn.execute(
                f"SELECT DISTINCT {q(cname)} FROM {q(self.tables[ti])} "
                f"WHERE {q(cname)} IS NOT NULL LIMIT 25"
            ).fetchall()
        except sqlite3.Error:
            return None
        vals = [r[0] for r in rows if r[0] not in (None, "")]
        return rng.choice(vals) if vals else None

    def low_threshold(self, ti, cname):
        """A round-ish value near the low end of a numeric column's range.

        Used for HAVING thresholds so the resulting query returns rows rather
        than an empty set.
        """
        try:
            row = self.conn.execute(
                f"SELECT MIN({q(cname)}), AVG({q(cname)}) FROM {q(self.tables[ti])} "
                f"WHERE {q(cname)} IS NOT NULL"
            ).fetchone()
        except sqlite3.Error:
            return None
        if not row or row[0] is None or row[1] is None:
            return None
        lo, avg = float(row[0]), float(row[1])
        if avg <= lo:
            return None
        thr = lo + (avg - lo) * 0.25
        return int(thr) if thr >= 10 else round(thr, 2)

    def fk_edges(self):
        """[(src_ti, src_col, tgt_ti, tgt_col)] resolved to table indices/names."""
        out = []
        for src, tgt in self.fks:
            s_ti, s_col = self.col_names[src]
            t_ti, t_col = self.col_names[tgt]
            if s_ti == -1 or t_ti == -1 or s_ti == t_ti:
                continue
            out.append((s_ti, s_col, t_ti, t_col))
        return out


def human(name: str) -> str:
    import re
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name).replace("_", " ")
    return re.sub(r"\s+", " ", s).strip().lower()


IRREGULAR_SINGULAR = {
    "people": "person", "children": "child", "men": "man", "women": "woman",
    "data": "record", "staff": "staff member",
}


def singular(phrase: str) -> str:
    """Rough singularizer for the LAST word of a phrase.

    Spider table names are usually plural ('countries', 'templates'), which
    makes 'each countries' read wrong. Heuristic only — English is English.
    """
    words = phrase.split()
    if not words:
        return phrase
    w = words[-1]
    if w in IRREGULAR_SINGULAR:
        words[-1] = IRREGULAR_SINGULAR[w]
    elif w.endswith("ies") and len(w) > 4:
        words[-1] = w[:-3] + "y"
    elif w.endswith("sses") or w.endswith("ches") or w.endswith("shes"):
        words[-1] = w[:-2]
    elif w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        words[-1] = w[:-1]
    return " ".join(words)


def plural(phrase: str) -> str:
    """Rough pluralizer for the LAST word of a phrase."""
    words = phrase.split()
    if not words:
        return phrase
    w = words[-1]
    inv = {v: k for k, v in IRREGULAR_SINGULAR.items()}
    if w in inv:
        words[-1] = inv[w]
    elif w.endswith("s") and not w.endswith("ss"):
        pass  # already plural
    elif w.endswith("y") and len(w) > 2 and w[-2] not in "aeiou":
        words[-1] = w[:-1] + "ies"
    elif w.endswith(("s", "x", "z", "ch", "sh")):
        words[-1] = w + "es"
    else:
        words[-1] = w + "s"
    return " ".join(words)


def phrase(table_name: str, col_name: str) -> str:
    """'continents' + 'Continent' -> 'continent', not 'continents continent'.

    Without this, table+column concatenation produces redundant noise that
    reads worse than anything a human would write — which muddies whether a
    model failed at SQL or at parsing the question.
    """
    t, c = human(table_name), human(col_name)
    tw, cw = set(singular(t).split()), set(singular(c).split())
    if cw and (cw <= tw or tw <= cw):
        return c
    # Partial overlap ('ref template type' + 'template type description') still
    # reads as gibberish when concatenated — drop the shared words from the
    # table side rather than repeating them.
    t_kept = [w for w in singular(t).split() if w not in cw]
    if not t_kept:
        return c
    return f"{' '.join(t_kept)} {c}"


def gen_simple(db, rng):
    out = []
    for ti, tname in enumerate(db.tables):
        if db.row_counts.get(ti, 0) < 2:
            continue
        th = plural(human(tname))
        ths = singular(human(tname))

        out.append((
            rng.choice([
                f"How many {th} are there?",
                f"Count the total number of {th}.",
                f"What is the total count of {th}?",
            ]),
            f"SELECT COUNT(*) FROM {q(tname)}",
        ))

        tcols = db.text_cols(ti)
        if tcols:
            ci, cname = rng.choice(tcols)
            if db.distinct_count(ti, cname) <= 25:
                out.append((
                    rng.choice([
                        f"List all distinct {human(cname)} values in {th}.",
                        f"What are the different {human(cname)} values recorded for {th}?",
                    ]),
                    f"SELECT DISTINCT {q(cname)} FROM {q(tname)}",
                ))

        label = db.label_col(ti)
        ncols = db.number_cols(ti)
        if label and ncols:
            _, lname = label
            _, nname = rng.choice(ncols)
            out.append((
                rng.choice([
                    f"Which {ths} has the highest {human(nname)}? Give its {human(lname)}.",
                    f"Return the {human(lname)} of the {ths} with the largest {human(nname)}.",
                ]),
                f"SELECT {q(lname)} FROM {q(tname)} ORDER BY {q(nname)} DESC LIMIT 1",
            ))

        if label and tcols:
            fci, fname = rng.choice(tcols)
            val = db.sample_value(ti, fname, rng)
            _, lname = label
            if val is not None and fname != lname:
                out.append((
                    rng.choice([
                        f"What is the {human(lname)} of the {ths} whose {human(fname)} is {val}?",
                        f"Find the {human(lname)} for the {ths} where {human(fname)} equals {val}.",
                    ]),
                    f"SELECT {q(lname)} FROM {q(tname)} WHERE {q(fname)} = {lit(val)}",
                ))
    return out


def gen_moderate(db, rng):
    out = []
    for ti, tname in enumerate(db.tables):
        if db.row_counts.get(ti, 0) < 3:
            continue
        th = plural(human(tname))

        tcols = db.text_cols(ti)
        for ci, cname in db.group_cols(ti):
            out.append((
                rng.choice([
                    f"How many {th} are there for each {human(cname)}?",
                    f"Count the {th} grouped by {human(cname)}.",
                    f"For each {human(cname)}, how many {th} are recorded?",
                ]),
                f"SELECT {q(cname)}, COUNT(*) FROM {q(tname)} GROUP BY {q(cname)}",
            ))
            break

        ncols = db.number_cols(ti)
        if ncols and tcols:
            _, nname = rng.choice(ncols)
            fci, fname = rng.choice(tcols)
            val = db.sample_value(ti, fname, rng)
            if val is not None:
                out.append((
                    rng.choice([
                        f"What is the average {human(nname)} of {th} whose {human(fname)} is {val}?",
                        f"Compute the mean {human(nname)} for {th} where {human(fname)} is {val}.",
                    ]),
                    f"SELECT AVG({q(nname)}) FROM {q(tname)} WHERE {q(fname)} = {lit(val)}",
                ))

    for s_ti, s_col, t_ti, t_col in db.fk_edges():
        if db.row_counts.get(s_ti, 0) < 2 or db.row_counts.get(t_ti, 0) < 2:
            continue
        s_tab, t_tab = db.tables[s_ti], db.tables[t_ti]
        s_label, t_label = db.label_col(s_ti), db.label_col(t_ti)
        if not t_label:
            continue
        _, t_lname = t_label
        t_ph = phrase(t_tab, t_lname)
        s_pl = plural(human(s_tab))
        join = (f"FROM {q(s_tab)} JOIN {q(t_tab)} "
                f"ON {q(s_tab)}.{q(s_col)} = {q(t_tab)}.{q(t_col)}")

        if s_label:
            _, s_lname = s_label
            out.append((
                rng.choice([
                    f"List each {phrase(s_tab, s_lname)} together with the {t_ph} of its {singular(human(t_tab))}.",
                    f"Show the {phrase(s_tab, s_lname)} of every {singular(human(s_tab))} alongside the related {t_ph}.",
                ]),
                f"SELECT {q(s_tab)}.{q(s_lname)}, {q(t_tab)}.{q(t_lname)} {join}",
            ))

        out.append((
            rng.choice([
                f"How many {s_pl} are linked to each {t_ph}?",
                f"For each {t_ph}, count the related {s_pl}.",
            ]),
            f"SELECT {q(t_tab)}.{q(t_lname)}, COUNT(*) {join} GROUP BY {q(t_tab)}.{q(t_lname)}",
        ))

        out.append((
            rng.choice([
                f"How many {s_pl} are there in total that are linked to a {singular(human(t_tab))}?",
                f"Count the {s_pl} that have a matching {singular(human(t_tab))}.",
            ]),
            f"SELECT COUNT(*) {join}",
        ))

        s_nums_m = db.number_cols(s_ti)
        if s_nums_m:
            _, s_nn = rng.choice(s_nums_m)
            out.append((
                rng.choice([
                    f"Which {t_ph} belongs to the {singular(human(s_tab))} with the highest {human(s_nn)}?",
                    f"Return the {t_ph} of the {singular(human(s_tab))} that has the largest {human(s_nn)}.",
                ]),
                f"SELECT {q(t_tab)}.{q(t_lname)} {join} "
                f"ORDER BY {q(s_tab)}.{q(s_nn)} DESC LIMIT 1",
            ))
            out.append((
                rng.choice([
                    f"What is the highest {human(s_nn)} among {s_pl} linked to a {singular(human(t_tab))}?",
                    f"Find the maximum {human(s_nn)} across {s_pl} that have a matching {singular(human(t_tab))}.",
                ]),
                f"SELECT MAX({q(s_tab)}.{q(s_nn)}) {join}",
            ))

    for ti, tname in enumerate(db.tables):
        if db.row_counts.get(ti, 0) < 3:
            continue
        for _, nname in db.number_cols(ti)[:1]:
            out.append((
                rng.choice([
                    f"What are the highest and lowest {human(nname)} among {plural(human(tname))}?",
                    f"Report the maximum and minimum {human(nname)} recorded for {plural(human(tname))}.",
                ]),
                f"SELECT MAX({q(nname)}), MIN({q(nname)}) FROM {q(tname)}",
            ))
    return out


def gen_complex(db, rng):
    out = []

    for s_ti, s_col, t_ti, t_col in db.fk_edges():
        if db.row_counts.get(s_ti, 0) < 3 or db.row_counts.get(t_ti, 0) < 2:
            continue
        s_tab, t_tab = db.tables[s_ti], db.tables[t_ti]
        t_label = db.label_col(t_ti)
        if not t_label:
            continue
        _, t_lname = t_label
        t_ph = phrase(t_tab, t_lname)
        s_pl = plural(human(s_tab))
        t_sg = singular(human(t_tab))
        join = (f"FROM {q(s_tab)} JOIN {q(t_tab)} "
                f"ON {q(s_tab)}.{q(s_col)} = {q(t_tab)}.{q(t_col)}")

        out.append((
            rng.choice([
                f"Which {t_sg} has the most {s_pl}? Return its {t_ph}.",
                f"Return the {t_ph} of the {t_sg} associated with the greatest number of {s_pl}.",
                f"Find the {t_ph} with the highest count of related {s_pl}.",
            ]),
            f"SELECT {q(t_tab)}.{q(t_lname)} {join} GROUP BY {q(t_tab)}.{q(t_lname)} "
            f"ORDER BY COUNT(*) DESC LIMIT 1",
        ))

        out.append((
            rng.choice([
                f"Which {t_ph} values have more than one related {singular(human(s_tab))}?",
                f"Show every {t_ph} that is linked to more than one {singular(human(s_tab))}.",
            ]),
            f"SELECT {q(t_tab)}.{q(t_lname)} {join} GROUP BY {q(t_tab)}.{q(t_lname)} "
            f"HAVING COUNT(*) > 1",
        ))

        # negation: target rows with no matching source rows
        out.append((
            rng.choice([
                f"Which {plural(human(t_tab))} have no {s_pl} at all? Give the {t_ph}.",
                f"List the {t_ph} of every {t_sg} that has never been referenced by a {singular(human(s_tab))}.",
            ]),
            f"SELECT {q(t_lname)} FROM {q(t_tab)} WHERE {q(t_col)} NOT IN "
            f"(SELECT {q(s_col)} FROM {q(s_tab)} WHERE {q(s_col)} IS NOT NULL)",
        ))

        s_nums = db.number_cols(s_ti)
        if s_nums:
            _, s_nname = rng.choice(s_nums)
            out.append((
                rng.choice([
                    f"What is the total {human(s_nname)} for each {t_ph}?",
                    f"Sum the {human(s_nname)} of {s_pl} grouped by {t_ph}.",
                ]),
                f"SELECT {q(t_tab)}.{q(t_lname)}, SUM({q(s_tab)}.{q(s_nname)}) {join} "
                f"GROUP BY {q(t_tab)}.{q(t_lname)}",
            ))
            out.append((
                rng.choice([
                    f"Which {t_ph} has the highest total {human(s_nname)} across its {s_pl}?",
                    f"Return the {t_ph} with the largest combined {human(s_nname)}.",
                ]),
                f"SELECT {q(t_tab)}.{q(t_lname)} {join} GROUP BY {q(t_tab)}.{q(t_lname)} "
                f"ORDER BY SUM({q(s_tab)}.{q(s_nname)}) DESC LIMIT 1",
            ))
            # Threshold pulled from the data (a low percentile) so the query
            # actually returns rows — a HAVING clause nothing satisfies makes a
            # useless test item.
            thr = db.low_threshold(s_ti, s_nname)
            if thr is not None:
                out.append((
                    rng.choice([
                        f"Which {t_ph} values have an average {human(s_nname)} greater than {thr}?",
                        f"Show each {t_ph} whose mean {human(s_nname)} exceeds {thr}.",
                    ]),
                    f"SELECT {q(t_tab)}.{q(t_lname)} {join} GROUP BY {q(t_tab)}.{q(t_lname)} "
                    f"HAVING AVG({q(s_tab)}.{q(s_nname)}) > {thr}",
                ))

    # two-hop chains: A -> B -> C, the shape single-join templates can't reach
    edges = db.fk_edges()
    by_src = defaultdict(list)
    for e in edges:
        by_src[e[0]].append(e)
    for a_ti, a_col, b_ti, b_col in edges:
        for b2_ti, b2_col, c_ti, c_col in by_src.get(b_ti, []):
            if c_ti in (a_ti, b_ti):
                continue
            if min(db.row_counts.get(x, 0) for x in (a_ti, b_ti, c_ti)) < 2:
                continue
            c_label = db.label_col(c_ti)
            if not c_label:
                continue
            _, c_lname = c_label
            a_tab, b_tab, c_tab = db.tables[a_ti], db.tables[b_ti], db.tables[c_ti]
            c_ph = phrase(c_tab, c_lname)
            join3 = (
                f"FROM {q(a_tab)} "
                f"JOIN {q(b_tab)} ON {q(a_tab)}.{q(a_col)} = {q(b_tab)}.{q(b_col)} "
                f"JOIN {q(c_tab)} ON {q(b_tab)}.{q(b2_col)} = {q(c_tab)}.{q(c_col)}"
            )
            out.append((
                rng.choice([
                    f"Which {c_ph} is associated with the most {plural(human(a_tab))}?",
                    f"Return the {c_ph} linked to the greatest number of {plural(human(a_tab))}.",
                ]),
                f"SELECT {q(c_tab)}.{q(c_lname)} {join3} "
                f"GROUP BY {q(c_tab)}.{q(c_lname)} ORDER BY COUNT(*) DESC LIMIT 1",
            ))
            out.append((
                rng.choice([
                    f"For each {c_ph}, how many {plural(human(a_tab))} are there?",
                    f"Count the {plural(human(a_tab))} associated with each {c_ph}.",
                ]),
                f"SELECT {q(c_tab)}.{q(c_lname)}, COUNT(*) {join3} "
                f"GROUP BY {q(c_tab)}.{q(c_lname)}",
            ))

    for ti, tname in enumerate(db.tables):
        if db.row_counts.get(ti, 0) < 4:
            continue
        label = db.label_col(ti)
        ncols = db.number_cols(ti)
        if not label or not ncols:
            continue
        _, lname = label
        _, nname = rng.choice(ncols)
        th = plural(human(tname))
        out.append((
            rng.choice([
                f"Which {th} have a {human(nname)} above the average {human(nname)}? Give their {human(lname)}.",
                f"Return the {human(lname)} of each {singular(human(tname))} whose {human(nname)} exceeds the overall average.",
            ]),
            f"SELECT {q(lname)} FROM {q(tname)} WHERE {q(nname)} > "
            f"(SELECT AVG({q(nname)}) FROM {q(tname)})",
        ))
        gcols = db.group_cols(ti)
        if gcols and ncols:
            gci, gname = gcols[0]
            out.append((
                rng.choice([
                    f"For each {human(gname)}, what is the average {human(nname)}, "
                    f"considering only groups whose average exceeds the overall average {human(nname)}?",
                    f"Show each {human(gname)} whose mean {human(nname)} is above the overall mean.",
                ]),
                f"SELECT {q(gname)}, AVG({q(nname)}) FROM {q(tname)} GROUP BY {q(gname)} "
                f"HAVING AVG({q(nname)}) > (SELECT AVG({q(nname)}) FROM {q(tname)})",
            ))
    return out


def verify(conn, sql):
    """Gold SQL must execute AND return at least one row.

    Empty results are excluded deliberately: a question whose correct answer is
    'no rows' is graded correct by any query that also happens to return
    nothing, including broken ones, which makes it a bad test item.
    """
    try:
        cur = conn.execute(sql)
        rows = cur.fetchall()
        return len(rows) > 0
    except sqlite3.Error:
        return False


def main():
    total = int(sys.argv[1]) if len(sys.argv) > 1 else TARGET_TOTAL
    scale = total / TARGET_TOTAL
    targets = {k: max(1, round(v * scale)) for k, v in TARGET_MIX.items()}

    rng = random.Random(SEED)
    tables = {t["db_id"]: t for t in json.loads((SPIDER / "tables.json").read_text())}
    db_root = next(p for p in SPIDER.rglob("database") if p.is_dir())
    eval_dbs = sorted(set(e["db_id"] for e in json.loads((DATA / "eval_sample.json").read_text())))

    pool = {"simple": [], "moderate": [], "complex": []}
    per_db_counts = defaultdict(lambda: defaultdict(int))

    for db_id in eval_dbs:
        sqlite_path = db_root / db_id / f"{db_id}.sqlite"
        if not sqlite_path.exists():
            print(f"skip {db_id}: no sqlite file")
            continue
        conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True, timeout=10)
        entry = tables[db_id]
        db = DbInfo(db_id, entry, conn)
        schema_text = build_schema_text(entry)

        for gen in (gen_simple, gen_moderate, gen_complex):
            for question, sql in gen(db, rng):
                if not verify(conn, sql):
                    continue
                bucket = sql_complexity_bucket(sql)
                pool[bucket].append({
                    "db_id": db_id,
                    "question": question,
                    "gold_sql": sql,
                    "complexity_bucket": bucket,
                    "sqlite_path": str(sqlite_path),
                    "schema_text": schema_text,
                })
                per_db_counts[db_id][bucket] += 1
        conn.close()

    print("verified candidate pool:")
    for b in ("simple", "moderate", "complex"):
        print(f"  {b:9} {len(pool[b]):5} candidates (target {targets[b]})")

    # Sample round-robin across databases so no single db dominates a bucket.
    selected = []
    for bucket, want in targets.items():
        by_db = defaultdict(list)
        for item in pool[bucket]:
            by_db[item["db_id"]].append(item)
        for items in by_db.values():
            rng.shuffle(items)
        picked, exhausted = [], False
        while len(picked) < want and not exhausted:
            exhausted = True
            for db_id in sorted(by_db):
                if by_db[db_id] and len(picked) < want:
                    picked.append(by_db[db_id].pop())
                    exhausted = False
        if len(picked) < want:
            print(f"  NOTE: only {len(picked)} {bucket} available, wanted {want}")
        selected.extend(picked)

    rng.shuffle(selected)
    for i, item in enumerate(selected):
        item["id"] = i

    OUT_PATH.write_text(json.dumps(selected, indent=2))

    from collections import Counter
    print(f"\nwrote {len(selected)} questions to {OUT_PATH}")
    print("bucket mix:", dict(Counter(e["complexity_bucket"] for e in selected)))
    print("distinct dbs:", len(set(e["db_id"] for e in selected)))


if __name__ == "__main__":
    main()
