import sqlite3
import sys

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0].lower() for row in cursor.fetchall()}
    
    if table_name.lower() in existing_tables:
        if table_name.startswith('sqlite_'):
            raise ValueError("Disallowed table name")
        table_name_quoted = table_name.replace('"', '""')
        table_name_quoted = f'"{table_name_quoted}"'
        cursor.execute(f"SELECT * FROM {table_name_quoted} ORDER BY rowid LIMIT {limit}")
        rows = cursor.fetchall()
    else:
        raise ValueError("Table not found")
    
    conn.close()
    return rows
