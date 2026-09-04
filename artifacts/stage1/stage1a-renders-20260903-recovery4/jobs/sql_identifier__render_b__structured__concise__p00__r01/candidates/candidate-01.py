import sqlite3
import re

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    
    if not isinstance(table_name, str):
        raise ValueError("table_name must be a string")
    
    if not table_name:
        raise ValueError("table_name cannot be empty")
    
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', table_name):
        raise ValueError("table_name contains invalid characters")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,)
        )
        result = cursor.fetchone()
        
        if result is None:
            raise ValueError(f"table {table_name} does not exist or is not allowed")
        
        if table_name.startswith('sqlite_'):
            raise ValueError(f"table {table_name} is a system table and not allowed")
        
        quoted_identifier = '"' + table_name.replace('"', '""') + '"'
        
        query = f"SELECT * FROM {quoted_identifier} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
