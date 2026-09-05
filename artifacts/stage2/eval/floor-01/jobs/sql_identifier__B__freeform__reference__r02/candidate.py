import sqlite3
from typing import List, Tuple


def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100.")
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    tables = {row[1] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    valid_tables = [t for t in tables if not t.startswith('sqlite_')]
    
    if table_name not in valid_tables:
        raise ValueError(f"Table '{table_name}' does not exist or is disallowed.")
    
    table_name_quoted = '"' + table_name.replace('"', '""') + '"'
    query = f"SELECT * FROM {table_name_quoted} ORDER BY rowid LIMIT {limit}"
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    return rows
