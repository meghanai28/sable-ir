import sqlite3
from typing import List, Tuple


def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")

    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        if table_name not in existing_tables or table_name.startswith("sqlite_"):
            raise ValueError(f"Table '{table_name}' does not exist or is a system table")

        escaped_table_name = f'"{table_name.replace('"', '""')}"'
        query = f"SELECT * FROM {escaped_table_name} ORDER BY rowid LIMIT {limit}"
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        raise ValueError(f"Database error: {e}") from e
