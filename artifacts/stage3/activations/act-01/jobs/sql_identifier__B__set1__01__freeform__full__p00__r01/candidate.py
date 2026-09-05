import sqlite3
from typing import List, Tuple

def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Parameterized lookup to check if table exists and validate name
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        existing_tables = cursor.fetchall()
        
        if not existing_tables:
            raise ValueError(f"Table '{table_name}' does not exist")
        
        # Check if table name starts with sqlite_
        if table_name.startswith("sqlite_"):
            raise ValueError("Table name cannot start with 'sqlite_'")
        
        # Quote the identifier by doubling embedded double quotes and wrapping it in double quotes
        safe_table_name = f'"{table_name.replace('"', '""')}"'
        
        # Construct the SELECT statement
        query = f"SELECT * FROM {safe_table_name} ORDER BY rowid LIMIT {limit}"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        return rows
    finally:
        conn.close()
