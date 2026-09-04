import sqlite3
import re

_ALLOWED_TABLE_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not _ALLOWED_TABLE_PATTERN.match(table_name):
        raise ValueError(f"Disallowed table name: {table_name}")
    if not 1 <= limit <= 100:
        raise ValueError(f"Limit must be between 1 and 100, got: {limit}")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT rowid, * FROM {table_name} ORDER BY rowid LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
