import sqlite3
from typing import List, Tuple


def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")

    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        cursor.execute(query)
        result = cursor.fetchone()
        if result is None:
            raise ValueError(f"Table {table_name} does not exist")
        table_name = result[0]
        if table_name.startswith("sqlite_"):
            raise ValueError(f"Table {table_name} is a system table and is not allowed")
        table_name = table_name.replace('"', '""')
        table_name = f'"{table_name}"'
        query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT {limit}"
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except sqlite3.Error as e:
        raise ValueError(f"Database error: {e}") from e
