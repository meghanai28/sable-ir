import sqlite3
import re

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100 inclusive")
    
    if not isinstance(table_name, str) or len(table_name) == 0:
        raise ValueError("invalid table name")
    
    if not isinstance(database_path, str) or len(database_path) == 0:
        raise ValueError("invalid database path")
    
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
        
        validated_table_name = result[0]
        
        if validated_table_name.startswith("sqlite_"):
            raise ValueError("disallowed table")
        
        def quote_identifier(ident):
            return '"' + ident.replace('"', '""') + '"'
        
        quoted_table = quote_identifier(validated_table_name)
        
        query = f"SELECT rowid, * FROM {quoted_table} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
