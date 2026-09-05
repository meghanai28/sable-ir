import sqlite3
from typing import List, Tuple

def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name=?
    """, (table_name,))
    
    result = cursor.fetchone()
    if result is None:
        raise ValueError(f"Table '{table_name}' does not exist")
    
    table_name_quoted = '"' + table_name.replace('"', '""') + '"'
    
    cursor.execute(f"SELECT * FROM {table_name_quoted} ORDER BY rowid LIMIT {limit}")
    
    rows = cursor.fetchall()
    conn.close()
    return rows
