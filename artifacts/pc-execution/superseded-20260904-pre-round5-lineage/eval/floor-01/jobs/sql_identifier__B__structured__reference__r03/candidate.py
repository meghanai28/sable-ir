import sqlite3
import re
from typing import List, Tuple


def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100.")

    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
    except sqlite3.Error:
        conn.close()
        raise ValueError("Invalid database path or no tables found.")

    if table_name not in tables:
        raise ValueError(f"Table '{table_name}' does not exist.")

    if table_name.startswith("sqlite_"):
        raise ValueError("Table name starts with 'sqlite_', which is disallowed.")

    quoted_table = '"' + table_name.replace('"', '""') + '"'

    query = f"SELECT * FROM {quoted_table} ORDER BY rowid LIMIT ?"
    cursor.execute(query, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows
