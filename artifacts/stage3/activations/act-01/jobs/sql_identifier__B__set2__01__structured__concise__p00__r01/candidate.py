import sqlite3
from typing import List, Tuple


def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")

    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        tables = [row[0] for row in cursor.fetchall()]
        if table_name not in tables:
            raise ValueError(f"Table '{table_name}' does not exist")
    except sqlite3.Error:
        raise ValueError(f"Invalid table name: {table_name}")
    finally:
        conn.close()

    table_name_quoted = f'"{table_name}"'
    query = f"SELECT * FROM {table_name_quoted} ORDER BY rowid LIMIT {limit}"
    cursor = sqlite3.connect(database_path).execute(query)
    rows = cursor.fetchall()
    return rows
