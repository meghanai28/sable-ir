import sqlite3
from typing import List, Tuple


def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")

    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        schema_query = "SELECT name FROM sqlite_master WHERE type='table' AND name=? ORDER BY name"
        cursor.execute(schema_query, (table_name,))
        table_names = [row[0] for row in cursor.fetchall()]
        if table_name not in table_names:
            raise ValueError(f"Table '{table_name}' does not exist")
    except sqlite3.Error as e:
        raise ValueError(f"Database error: {e}")

    if table_name.startswith("sqlite_"):
        raise ValueError("Table name starts with 'sqlite_'")

    escaped_table_name = '"' + table_name.replace('"', '""') + '"'
    query = f"SELECT * FROM {escaped_table_name} ORDER BY rowid LIMIT {limit}"

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows
