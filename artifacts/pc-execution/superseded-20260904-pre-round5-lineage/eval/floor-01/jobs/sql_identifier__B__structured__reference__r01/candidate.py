import sqlite3
import os

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        schema_query = """
            SELECT name, sql FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        cursor.execute(schema_query, (table_name,))
        table_info = cursor.fetchone()
        
        if table_info is None:
            raise ValueError(f"Table '{table_name}' does not exist")
        
        if table_info[0].startswith('sqlite_'):
            raise ValueError(f"Table '{table_name}' is a system table")
        
        quoted_name = '"' + table_name.replace('"', '""') + '"'
        select_query = f"SELECT * FROM {quoted_name} ORDER BY rowid LIMIT ?"
        
        cursor.execute(select_query, (limit,))
        rows = cursor.fetchall()
        
        conn.close()
        return rows
    except sqlite3.Error as e:
        raise ValueError(f"Database error: {e}")
