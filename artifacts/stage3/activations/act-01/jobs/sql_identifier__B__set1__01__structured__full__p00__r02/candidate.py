import sqlite3
from typing import List, Tuple

def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100.")
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name 
        FROM sqlite_master 
        WHERE type='table' 
        AND name=? 
        AND name NOT LIKE 'sqlite_%';
    """, (table_name,))
    
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    if table_name not in existing_tables:
        raise ValueError(f"Table '{table_name}' does not exist or is a system table.")
    
    cursor.execute(f"SELECT * FROM {table_name} ORDER BY rowid LIMIT {limit}")
    rows = cursor.fetchall()
    conn.close()
    
    return rows
