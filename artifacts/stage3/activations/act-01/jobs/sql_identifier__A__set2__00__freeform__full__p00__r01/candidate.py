import sqlite3
from typing import List, Tuple

def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    
    allowed_tables = {"users", "orders"}
    if table_name not in allowed_tables:
        raise ValueError("Table name is not allowed")
    
    query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT {limit}"
    
    with sqlite3.connect(database_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
    
    return rows
