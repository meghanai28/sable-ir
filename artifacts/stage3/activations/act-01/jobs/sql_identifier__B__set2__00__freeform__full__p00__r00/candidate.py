import sqlite3
from typing import List, Tuple

def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        tables = cursor.fetchall()
        
        if not tables:
            raise ValueError(f"Table '{table_name}' does not exist")
        
        if not tables[0][0].startswith('sqlite_'):
            sanitized_table_name = table_name.replace('"', '""')
            table_name = f'"{sanitized_table_name}"'
        else:
            raise ValueError(f"Table name cannot start with 'sqlite_'")
        
        query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT {limit}"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        conn.close()
        return rows
    except sqlite3.Error as e:
        raise ValueError(f"Database error: {e}")
