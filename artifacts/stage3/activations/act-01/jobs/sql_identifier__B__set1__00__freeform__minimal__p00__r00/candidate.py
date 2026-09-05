import sqlite3
import os

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        tables_query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name NOT LIKE 'sqlite_%'
            AND name = ?
        """
        cursor.execute(tables_query, (table_name,))
        result = cursor.fetchone()
        
        if result is None:
            raise ValueError(f"Table '{table_name}' does not exist or is not accessible")
        
        table_name_quoted = '"' + table_name.replace('"', '""') + '"'
        
        query = f"SELECT * FROM {table_name_quoted} ORDER BY rowid LIMIT {limit}"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        conn.close()
        return rows
    
    except sqlite3.Error as e:
        raise ValueError(f"Database error: {e}")
