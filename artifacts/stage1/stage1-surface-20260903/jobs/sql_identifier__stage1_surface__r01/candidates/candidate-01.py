import sqlite3
import re

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        raise ValueError("Disallowed table name")
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT rowid FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if cursor.fetchone() is None:
            raise ValueError("Disallowed table name")
        
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
