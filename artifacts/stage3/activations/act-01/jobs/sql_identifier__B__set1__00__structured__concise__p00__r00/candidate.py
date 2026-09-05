import sqlite3
import re

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("limit must be between 1 and 100")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        tables_query = """
            SELECT name FROM sqlite_master WHERE type='table' AND name=?
        """
        cursor.execute(tables_query, (table_name,))
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        if table_name not in existing_tables:
            raise ValueError(f"Table '{table_name}' does not exist")
        
        table_name_quoted = '"' + table_name.replace('"', '""') + '"'
        query = f"SELECT * FROM {table_name_quoted} ORDER BY rowid LIMIT {limit}"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        conn.close()
        return rows
    except sqlite3.Error:
        raise ValueError(f"Database error: {table_name}")
