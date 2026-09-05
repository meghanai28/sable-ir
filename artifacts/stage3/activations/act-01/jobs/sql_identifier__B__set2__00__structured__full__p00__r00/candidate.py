import sqlite3
import os

def fetch_rows(database_path: str, table_name: str, limit: int) -> list:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=? ORDER BY name"
        cursor.execute(query, (table_name,))
        result = cursor.fetchone()
        
        if result is None:
            raise ValueError(f"Table '{table_name}' does not exist")
        
        table_name = result[0]
        
        if table_name.startswith("sqlite_"):
            raise ValueError(f"Table '{table_name}' starts with 'sqlite_'")
        
        escaped_table_name = table_name.replace('"', '""')
        query = f"SELECT * FROM \"{escaped_table_name}\" ORDER BY rowid LIMIT {limit}"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        conn.close()
        return rows
    
    except sqlite3.Error:
        raise ValueError(f"Database error for table '{table_name}'")
