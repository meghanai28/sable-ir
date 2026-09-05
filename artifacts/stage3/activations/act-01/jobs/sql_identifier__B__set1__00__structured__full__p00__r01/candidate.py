import sqlite3
import os

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    query = "SELECT name FROM sqlite_master WHERE type='table' AND name=? ORDER BY name"
    cursor.execute(query, (table_name,))
    result = cursor.fetchone()
    
    if result is None:
        raise ValueError(f"Table '{table_name}' does not exist")
    
    table_name = result[0]
    if table_name.startswith("sqlite_"):
        raise ValueError(f"Table '{table_name}' is a system table and is not allowed")
    
    safe_table_name = f'"{table_name}"'
    
    query = f"SELECT * FROM {safe_table_name} ORDER BY rowid LIMIT {limit}"
    cursor.execute(query)
    
    rows = cursor.fetchall()
    conn.close()
    
    return rows
