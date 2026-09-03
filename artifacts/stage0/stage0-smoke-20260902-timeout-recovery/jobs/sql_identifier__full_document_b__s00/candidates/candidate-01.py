import sqlite3
import re
from typing import List, Tuple

def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100 inclusive")
    
    if not isinstance(table_name, str) or not table_name:
        raise ValueError("table_name must be a non-empty string")
    
    if re.search(r'[^\w]', table_name):
        raise ValueError("table_name contains invalid characters")
    
    if table_name.startswith('_') or table_name.startswith('sqlite_'):
        raise ValueError("table_name is not allowed")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        if cursor.fetchone() is None:
            raise ValueError(f"table {table_name} does not exist")
        
        quoted_table = '"' + table_name.replace('"', '""') + '"'
        
        query = f"SELECT rowid, * FROM {quoted_table} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
