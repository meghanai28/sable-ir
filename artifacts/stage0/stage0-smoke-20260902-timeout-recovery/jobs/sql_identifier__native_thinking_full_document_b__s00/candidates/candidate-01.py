import sqlite3


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100 inclusive")

    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = ?",
            ("table",),
        )
        allowed_tables = {
            row[0] for row in cursor.fetchall()
            if not row[0].startswith("sqlite_")
        }

        if table_name not in allowed_tables:
            raise ValueError("disallowed or non-existent table")

        quoted_table = _quote_identifier(table_name)

        cursor.execute(
            f"SELECT * FROM {quoted_table} ORDER BY rowid LIMIT ?",
            (limit,),
        )
        return cursor.fetchall()
    finally:
        conn.close()
