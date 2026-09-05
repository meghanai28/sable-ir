import sqlite3
from typing import List, Tuple

def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    tables_query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
        AND name NOT LIKE 'sqlite_%'
    """
    cursor.execute(tables_query, (table_name,))
    result = cursor.fetchone()
    
    if result is None:
        raise ValueError(f"Table '{table_name}' does not exist or is a system table")
    
    safe_table_name = f'"{result[0]}"'
    
    query = f"SELECT * FROM {safe_table_name} ORDER BY rowid LIMIT {limit}"
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    return rows
