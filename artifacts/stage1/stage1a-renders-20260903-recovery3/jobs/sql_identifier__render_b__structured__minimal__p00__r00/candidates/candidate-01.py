import sqlite3


def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("limit must be between 1 and 100")

    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        )
        if cursor.fetchone() is None:
            raise ValueError("disallowed table")

        quoted_table = '"' + table_name.replace('"', '""') + '"'
        query = f"SELECT * FROM {quoted_table} ORDER BY rowid LIMIT ?"

        cursor.execute(query, (limit,))
        rows = cursor.fetchall()

        return rows
    finally:
        conn.close()
