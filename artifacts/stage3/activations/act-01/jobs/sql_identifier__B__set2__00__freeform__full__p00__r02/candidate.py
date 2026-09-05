import sqlite3
from typing import List, Tuple

def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        valid_tables = {row[0] for row in tables}
        
        if table_name not in valid_tables or table_name.startswith('sqlite_'):
            raise ValueError("Disallowed table")
        
        table_name_escaped = table_name.replace('"', '""')
        safe_table_name = f'"{table_name_escaped}"'
        
        cursor.execute(f"SELECT * FROM {safe_table_name} ORDER BY rowid LIMIT {limit}")
        rows = cursor.fetchall()
        
        conn.close()
        return rows
    except sqlite3.Error:
        raise ValueError("Database error")
