import sqlite3
import os

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    
    if not os.path.exists(database_path):
        raise ValueError(f"Database file not found: {database_path}")
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    try:
        catalog_query = "SELECT name FROM sqlite_master WHERE type='table' AND name=? ORDER BY name"
        cursor.execute(catalog_query, (table_name,))
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        if table_name not in existing_tables:
            raise ValueError(f"Table '{table_name}' does not exist in the database")
        
        if table_name.startswith("sqlite_"):
            raise ValueError(f"Table '{table_name}' is a system table and cannot be queried")
        
        quoted_table_name = f'"{table_name}"'
        query = f"SELECT * FROM {quoted_table_name} ORDER BY rowid LIMIT {limit}"
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        return results
    finally:
        conn.close()
