import sqlite3
import re

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        valid_tables = [t[0] for t in tables]
        
        if table_name not in valid_tables:
            raise ValueError(f"Table '{table_name}' does not exist or is not accessible")
        
        escaped_table_name = table_name.replace('"', '""')
        query = f'SELECT * FROM "{escaped_table_name}" ORDER BY rowid LIMIT {limit}'
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except sqlite3.Error as e:
        raise ValueError(f"Database error: {e}")
