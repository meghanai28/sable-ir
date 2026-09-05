import sqlite3
from typing import List, Tuple


def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")

    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=? ORDER BY name", (table_name,))
        table_names = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
    except sqlite3.Error:
        raise ValueError(f"Table '{table_name}' does not exist or is invalid")

    if table_name not in table_names or table_name.startswith("sqlite_"):
        raise ValueError(f"Table '{table_name}' is disallowed")

    escaped_table_name = table_name.replace('"', '""')
    query = f'SELECT * FROM "{escaped_table_name}" ORDER BY rowid LIMIT {limit}'
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows
