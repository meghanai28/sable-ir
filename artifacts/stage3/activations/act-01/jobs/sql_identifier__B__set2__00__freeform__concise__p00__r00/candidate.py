import sqlite3
import re

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Validate table name using sqlite_master
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            raise ValueError(f"Table '{table_name}' does not exist")
        
        # Check if table name starts with sqlite_
        if table_name.startswith('sqlite_'):
            raise ValueError("Table name must not start with 'sqlite_'")
        
        # Escape double quotes in table name
        escaped_table_name = table_name.replace('"', '""')
        safe_table_name = f'"{escaped_table_name}"'
        
        # Construct and execute the query
        query = f"SELECT * FROM {safe_table_name} ORDER BY rowid LIMIT {limit}"
        cursor.execute(query)
        
        # Fetch results
        rows = cursor.fetchall()
        conn.close()
        
        return rows
    except sqlite3.Error as e:
        raise ValueError(f"Database error: {e}")
