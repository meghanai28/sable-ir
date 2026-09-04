import sqlite3
import re

def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100 inclusive")
    
    if not isinstance(table_name, str):
        raise ValueError("table_name must be a string")
    
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
        
        quoted_table = _quote_identifier(table_name)
        
        query = f"SELECT * FROM {quoted_table} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
