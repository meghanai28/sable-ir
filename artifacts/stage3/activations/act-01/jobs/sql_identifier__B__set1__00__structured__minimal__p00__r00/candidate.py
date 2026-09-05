import sqlite3
import os

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    try:
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=? ORDER BY name"
        cursor.execute(query, (table_name,))
        table_name_result = cursor.fetchone()
        
        if not table_name_result:
            raise ValueError(f"Table '{table_name}' does not exist")
        
        actual_table_name = table_name_result[0]
        
        if actual_table_name.startswith("sqlite_"):
            raise ValueError(f"Table '{actual_table_name}' is a system table and is not allowed")
        
        quoted_table_name = f'"{actual_table_name}"'
        
        query = f"SELECT * FROM {quoted_table_name} ORDER BY rowid LIMIT {limit}"
        cursor.execute(query)
        
        rows = cursor.fetchall()
    finally:
        conn.close()
    
    return rows
