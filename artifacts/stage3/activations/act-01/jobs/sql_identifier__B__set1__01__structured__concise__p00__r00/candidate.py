import sqlite3
from typing import List, Tuple

def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        tables_query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name NOT LIKE 'sqlite_%'
            AND name=?
        """
        cursor.execute(tables_query, (table_name,))
        existing_tables = cursor.fetchall()
        
        if not existing_tables:
            raise ValueError(f"Table '{table_name}' does not exist")
        
        table_name = existing_tables[0][0]
        
        select_query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT {limit}"
        cursor.execute(select_query)
        
        rows = cursor.fetchall()
        conn.close()
        
        return rows
    except sqlite3.Error as e:
        raise ValueError(f"Database error: {e}")
