import sqlite3
import re


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")

    if not isinstance(table_name, str) or len(table_name) == 0:
        raise ValueError("disallowed table")

    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,)
        )
        result = cursor.fetchone()

        if result is None:
            raise ValueError("disallowed table")

        if table_name.startswith("sqlite_"):
            raise ValueError("disallowed table")

        def quote_identifier(identifier):
            return '"' + identifier.replace('"', '""') + '"'

        quoted_table = quote_identifier(table_name)

        query = f"SELECT rowid, * FROM {quoted_table} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))

        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
