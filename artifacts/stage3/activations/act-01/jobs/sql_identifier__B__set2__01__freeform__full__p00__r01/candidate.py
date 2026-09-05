import sqlite3
from typing import List, Tuple, Any

def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple[Any, ...]]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        tables = cursor.fetchall()
        
        if not tables:
            raise ValueError(f"Table '{table_name}' does not exist")
        
        if tables[0][0] != table_name:
            raise ValueError(f"Table '{table_name}' does not exist")
        
        query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT {limit}"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        return rows
    finally:
        conn.close()
