import sqlite3
from typing import List, Tuple

def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        if table_name not in existing_tables:
            raise ValueError(f"Table '{table_name}' does not exist")
        
        if table_name.startswith("sqlite_"):
            raise ValueError("Table name starts with 'sqlite_', which is disallowed")
        
        quoted_name = table_name.replace('"', '""')
        safe_table_name = f'"{quoted_name}"'
        
        query = f"SELECT * FROM {safe_table_name} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
