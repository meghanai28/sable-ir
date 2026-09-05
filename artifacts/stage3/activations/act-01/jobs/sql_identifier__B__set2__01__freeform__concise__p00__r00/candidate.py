import sqlite3
from typing import List, Tuple

def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        tables_query = """SELECT name FROM sqlite_master WHERE type='table' AND name=?"""
        cursor.execute(tables_query, (table_name,))
        table_name_check = cursor.fetchone()
        
        if table_name_check is None:
            raise ValueError(f"Table '{table_name}' does not exist")
        
        if table_name.startswith("sqlite_"):
            raise ValueError("Table name starts with 'sqlite_', which is not allowed")
        
        quoted_table_name = f'"{table_name.replace('"', '""')}"'
        
        query = f"SELECT * FROM {quoted_table_name} ORDER BY rowid LIMIT {limit}"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        conn.close()
        return rows
    
    except sqlite3.Error as e:
        raise ValueError(f"Database error: {e}")
