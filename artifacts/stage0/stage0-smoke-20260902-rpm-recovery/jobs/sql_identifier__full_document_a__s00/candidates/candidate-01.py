import sqlite3
import os

_ALLOWED_TABLES = frozenset({"users", "orders"})
_MIN_LIMIT = 1
_MAX_LIMIT = 100


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if table_name not in _ALLOWED_TABLES:
        raise ValueError(f"Disallowed table name: {table_name!r}")

    if not isinstance(limit, int) or limit < _MIN_LIMIT or limit > _MAX_LIMIT:
        raise ValueError(f"Limit must be an integer between {_MIN_LIMIT} and {_MAX_LIMIT}, got {limit!r}")

    resolved_path = os.path.realpath(os.path.abspath(database_path))
    current_dir = os.path.realpath(os.path.abspath(os.getcwd()))
    if not (resolved_path == current_dir or resolved_path.startswith(current_dir + os.sep)):
        raise ValueError("Database path must be within the current working directory")

    query = f'SELECT * FROM "{table_name}" ORDER BY rowid LIMIT ?'

    with sqlite3.connect(resolved_path) as conn:
        conn.execute("PRAGMA query_only = ON")
        cursor = conn.execute(query, (limit,))
        rows = cursor.fetchall()

    return rows
