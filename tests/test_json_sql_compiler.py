"""Execution checks for JSON plans, including binding order and rejection."""

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from json_sql_compiler import JsonSqlCompiler, PlanError


class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "sample.sqlite"
        with sqlite3.connect(self.db) as connection:
            connection.executescript("""
                CREATE TABLE people (id INTEGER, name TEXT, team_id INTEGER);
                CREATE TABLE teams (id INTEGER, name TEXT);
                INSERT INTO people VALUES (1, 'Ada', 2), (2, 'Ben', 2), (3, 'Cal', 1);
                INSERT INTO teams VALUES (1, 'Alpha'), (2, 'Beta');
            """)

    def tearDown(self):
        self.temp.cleanup()

    def execute(self, plan):
        sql, params = JsonSqlCompiler(self.db).compile(plan)
        with sqlite3.connect(self.db) as connection:
            return connection.execute(sql, params).fetchall(), sql, params

    def test_join_with_literals_in_select_on_and_where(self):
        plan = {"select": [{"literal": "label"}, {"col": "p.name"}],
                "from": {"table": "people", "as": "p"},
                "joins": [{"table": "teams", "as": "t", "on": {"op": "eq", "args": [
                    {"col": "p.team_id"}, {"func": "coalesce", "args": [
                        {"col": "t.id"}, {"literal": -1}]}]}}],
                "where": {"op": "eq", "args": [{"col": "t.name"}, {"literal": "Beta"}]}}
        rows, _, params = self.execute(plan)
        self.assertEqual(rows, [("label", "Ada"), ("label", "Ben")])
        self.assertEqual(params, ("label", -1, "Beta"))

    def test_nested_argmax(self):
        plan = {"select": [{"col": "name"}], "from": {"table": "people"},
                "where": {"op": "eq", "args": [{"col": "team_id"},
                    {"argmax": {"table": "teams", "by": "id", "value": "id"}}]}}
        rows, _, _ = self.execute(plan)
        self.assertEqual(rows, [("Ada",), ("Ben",)])

    def test_unknown_column_rejected(self):
        plan = {"select": [{"col": "password"}], "from": {"table": "people"}}
        with self.assertRaises(PlanError):
            self.execute(plan)


if __name__ == "__main__":
    unittest.main()
