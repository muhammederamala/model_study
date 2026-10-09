"""Compile a restricted JSON SELECT plan into parameterized SQLite SQL.

The model never supplies SQL fragments. Table and column names must exist in
the target database; values become bound parameters. Unsupported plans fail
explicitly so a JSON-run score includes coverage failures.
"""

import re
import sqlite3
from pathlib import Path


class PlanError(ValueError):
    pass


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
FUNCTIONS = {"count", "sum", "avg", "min", "max", "abs", "round", "lower", "upper", "length", "coalesce"}
BINARY = {"eq": "=", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=",
          "like": "LIKE", "not_like": "NOT LIKE", "add": "+", "sub": "-", "mul": "*", "div": "/"}
SET_OPS = {"union": "UNION", "union_all": "UNION ALL", "intersect": "INTERSECT", "except": "EXCEPT"}


def quote(name):
    return '"' + name.replace('"', '""') + '"'


class JsonSqlCompiler:
    def __init__(self, sqlite_path):
        self.sqlite_path = Path(sqlite_path)
        self.catalog = {}
        with sqlite3.connect(f"file:{self.sqlite_path}?mode=ro", uri=True) as connection:
            for (table,) in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') "
                    "AND name NOT LIKE 'sqlite_%'"):
                columns = connection.execute(f"PRAGMA table_info({quote(table)})").fetchall()
                self.catalog[table.lower()] = (table, {row[1].lower(): row[1] for row in columns})
        self.params = []
        self.nodes = 0

    def compile(self, plan):
        self.params = []
        self.nodes = 0
        sql = self._query(plan, ())
        order = []
        sql = re.sub(r"\?/\*json_param_(\d+)\*/", lambda match: self._bind(match, order), sql)
        return sql, tuple(self.params[index] for index in order)

    @staticmethod
    def _bind(match, order):
        order.append(int(match.group(1)))
        return "?"

    def _tick(self, value):
        self.nodes += 1
        if self.nodes > 250:
            raise PlanError("plan exceeds 250 nodes")
        if not isinstance(value, dict):
            raise PlanError("plan nodes must be objects")

    def _table(self, table):
        if not isinstance(table, str) or table.lower() not in self.catalog:
            raise PlanError(f"unknown table: {table!r}")
        return self.catalog[table.lower()][0]

    def _source(self, source, outer_scopes):
        self._tick(source)
        if "table" in source:
            table = self._table(source["table"])
            alias = source.get("as", table)
            if not isinstance(alias, str) or ("as" in source and not IDENTIFIER.fullmatch(alias)):
                raise PlanError(f"invalid table alias: {alias!r}")
            return f"{quote(table)} AS {quote(alias)}", {alias.lower(): table}
        if "query" in source:
            alias = source.get("as")
            if not isinstance(alias, str) or not IDENTIFIER.fullmatch(alias):
                raise PlanError("subquery source requires a simple alias")
            sql = self._query(source["query"], outer_scopes)
            return f"({sql}) AS {quote(alias)}", {alias.lower(): None}
        raise PlanError("source needs table or query")

    def _column(self, value, scopes):
        if not isinstance(value, str) or value.count(".") > 1:
            raise PlanError(f"invalid column: {value!r}")
        parts = value.split(".")
        if len(parts) == 2:
            qualifier, column = parts
            for scope in scopes:
                table = scope.get(qualifier.lower())
                if table is not None:
                    actual = self.catalog[table.lower()][1].get(column.lower())
                    if actual:
                        return f"{quote(qualifier)}.{quote(actual)}"
                elif qualifier.lower() in scope:
                    if not IDENTIFIER.fullmatch(column):
                        raise PlanError(f"invalid subquery column: {column!r}")
                    return f"{quote(qualifier)}.{quote(column)}"
            raise PlanError(f"unknown qualified column: {value!r}")
        column = parts[0]
        for scope in scopes:
            matches = [(alias, self.catalog[table.lower()][1][column.lower()])
                       for alias, table in scope.items()
                       if table is not None and column.lower() in self.catalog[table.lower()][1]]
            if len(matches) == 1:
                alias, actual = matches[0]
                return f"{quote(alias)}.{quote(actual)}"
            if len(matches) > 1:
                raise PlanError(f"ambiguous column: {column!r}")
        raise PlanError(f"unknown column: {column!r}")

    def _expr(self, node, scopes):
        self._tick(node)
        if "col" in node:
            return self._column(node["col"], scopes)
        if "literal" in node:
            value = node["literal"]
            if not isinstance(value, (str, int, float, bool, type(None))):
                raise PlanError("literal must be a scalar")
            self.params.append(value)
            return f"?/*json_param_{len(self.params) - 1}*/"
        if node.get("star") is True:
            return "*"
        if "subquery" in node:
            return f"({self._query(node['subquery'], scopes)})"
        if "values" in node:
            values = node["values"]
            if not isinstance(values, list) or not values:
                raise PlanError("values requires a nonempty list")
            return "(" + ", ".join(self._expr({"literal": value}, scopes) for value in values) + ")"
        if "argmax" in node:
            spec = node["argmax"]
            if not isinstance(spec, dict):
                raise PlanError("argmax must be an object")
            table = spec.get("table")
            value = spec.get("value")
            by = spec.get("by")
            if not all(isinstance(item, str) for item in (table, value, by)):
                raise PlanError("argmax requires table, value, and by")
            query = {"select": [{"col": value}], "from": {"table": table},
                     "order_by": [{"expr": {"col": by}, "direction": "desc"}], "limit": 1}
            if "where" in spec:
                query["where"] = spec["where"]
            return f"({self._query(query, scopes)})"
        if "func" in node:
            name = node["func"]
            if not isinstance(name, str) or name.lower() not in FUNCTIONS:
                raise PlanError(f"unsupported function: {name!r}")
            args = node.get("args", [])
            if not isinstance(args, list) or not args:
                raise PlanError("function requires args")
            if any(isinstance(arg, dict) and arg.get("star") is True for arg in args) and name.lower() != "count":
                raise PlanError("only COUNT accepts *")
            rendered = ", ".join(self._expr(arg, scopes) for arg in args)
            distinct = "DISTINCT " if node.get("distinct") is True else ""
            return f"{name.upper()}({distinct}{rendered})"
        if "op" in node:
            op = node["op"]
            args = node.get("args", [])
            if not isinstance(args, list):
                raise PlanError("operator args must be a list")
            if op in BINARY and len(args) == 2:
                return f"({self._expr(args[0], scopes)} {BINARY[op]} {self._expr(args[1], scopes)})"
            if op in ("and", "or") and len(args) >= 2:
                separator = " AND " if op == "and" else " OR "
                return "(" + separator.join(self._expr(arg, scopes) for arg in args) + ")"
            if op == "not" and len(args) == 1:
                return f"(NOT {self._expr(args[0], scopes)})"
            if op in ("in", "not_in") and len(args) == 2:
                left = self._expr(args[0], scopes)
                right = self._expr(args[1], scopes)
                if not right.startswith("("):
                    raise PlanError("IN right side must be values or subquery")
                return f"({left} {'NOT IN' if op == 'not_in' else 'IN'} {right})"
            if op == "between" and len(args) == 3:
                return f"({self._expr(args[0], scopes)} BETWEEN {self._expr(args[1], scopes)} AND {self._expr(args[2], scopes)})"
            if op in ("is_null", "is_not_null") and len(args) == 1:
                return f"({self._expr(args[0], scopes)} IS {'NOT ' if op == 'is_not_null' else ''}NULL)"
            if op == "exists" and len(args) == 1 and isinstance(args[0], dict) and "subquery" in args[0]:
                return f"EXISTS {self._expr(args[0], scopes)}"
            raise PlanError(f"unsupported operator or arity: {op!r}")
        raise PlanError(f"unknown expression node: {list(node)}")

    def _query(self, query, outer_scopes):
        self._tick(query)
        if len(outer_scopes) > 8:
            raise PlanError("query nesting exceeds 8 levels")
        if "set_op" in query:
            op = query["set_op"]
            parts = query.get("queries")
            if op not in SET_OPS or not isinstance(parts, list) or len(parts) < 2:
                raise PlanError("set_op requires supported operator and at least two queries")
            if any("order_by" in part or "limit" in part for part in parts):
                raise PlanError("set_op members cannot have order_by or limit")
            sql = f" {SET_OPS[op]} ".join(self._query(part, outer_scopes) for part in parts)
            return sql
        source = query.get("from")
        if not isinstance(source, dict):
            raise PlanError("query requires from source")
        from_sql, local = self._source(source, outer_scopes)
        joins_sql = []
        joins = query.get("joins", [])
        if not isinstance(joins, list) or len(joins) > 12:
            raise PlanError("joins must be a list of at most 12")
        for join in joins:
            self._tick(join)
            kind = join.get("kind", "inner")
            if kind not in ("inner", "left", "cross"):
                raise PlanError(f"unsupported join kind: {kind!r}")
            joined, names = self._source(join, (local,) + outer_scopes)
            if any(alias in local for alias in names):
                raise PlanError("duplicate table alias")
            local.update(names)
            if kind == "cross":
                joins_sql.append(f"CROSS JOIN {joined}")
            else:
                if "on" not in join:
                    raise PlanError("join requires on expression")
                on_sql = self._expr(join["on"], (local,) + outer_scopes)
                joins_sql.append(f"{'LEFT' if kind == 'left' else 'INNER'} JOIN {joined} ON {on_sql}")
        scopes = (local,) + outer_scopes
        columns = query.get("select")
        if not isinstance(columns, list) or not columns or len(columns) > 30:
            raise PlanError("select must contain 1 to 30 expressions")
        select_sql = []
        for item in columns:
            if not isinstance(item, dict):
                raise PlanError("select items must be objects")
            alias = item.get("as")
            value = {key: val for key, val in item.items() if key != "as"}
            expr_sql = self._expr(value, scopes)
            if alias is not None:
                if not isinstance(alias, str) or not IDENTIFIER.fullmatch(alias):
                    raise PlanError("invalid select alias")
                expr_sql += f" AS {quote(alias)}"
            select_sql.append(expr_sql)
        sql = "SELECT " + ("DISTINCT " if query.get("distinct") is True else "")
        sql += ", ".join(select_sql) + " FROM " + from_sql
        if joins_sql:
            sql += " " + " ".join(joins_sql)
        if "where" in query:
            sql += " WHERE " + self._expr(query["where"], scopes)
        if "group_by" in query:
            groups = query["group_by"]
            if not isinstance(groups, list) or not groups:
                raise PlanError("group_by must be a nonempty list")
            sql += " GROUP BY " + ", ".join(self._expr(value, scopes) for value in groups)
        if "having" in query:
            sql += " HAVING " + self._expr(query["having"], scopes)
        if "order_by" in query:
            orders = query["order_by"]
            if not isinstance(orders, list) or not orders:
                raise PlanError("order_by must be a nonempty list")
            chunks = []
            for order in orders:
                if not isinstance(order, dict) or order.get("direction", "asc") not in ("asc", "desc"):
                    raise PlanError("invalid order_by entry")
                chunks.append(self._expr(order["expr"], scopes) + " " + order.get("direction", "asc").upper())
            sql += " ORDER BY " + ", ".join(chunks)
        if "limit" in query:
            limit = query["limit"]
            if type(limit) is not int or not 1 <= limit <= 100000:
                raise PlanError("limit must be an integer from 1 to 100000")
            sql += f" LIMIT {limit}"
        return sql
