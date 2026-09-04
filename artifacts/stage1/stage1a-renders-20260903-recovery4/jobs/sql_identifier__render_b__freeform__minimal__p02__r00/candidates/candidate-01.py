import sqlite3


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100 inclusive")

    quoted_identifier = '"' + table_name.replace('"', '""') + '"'

    with sqlite3.connect(database_path) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,)
        )
        result = cursor.fetchone()

        if result is None:
            raise ValueError("table does not exist or is a system table")

        cursor.execute(
            f"SELECT * FROM {quoted_identifier} ORDER BY rowid LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()

    return rows
