import sqlite3
import re

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100 inclusive")
    
    if not isinstance(table_name, str) or len(table_name) == 0:
        raise ValueError("disallowed table")
    
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', table_name):
        raise ValueError("disallowed table")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,)
        )
        result = cursor.fetchone()
        
        if result is None:
            raise ValueError("disallowed table")
        
        quoted_identifier = '"' + table_name.replace('"', '""') + '"'
        
        query = f"SELECT * FROM {quoted_identifier} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
