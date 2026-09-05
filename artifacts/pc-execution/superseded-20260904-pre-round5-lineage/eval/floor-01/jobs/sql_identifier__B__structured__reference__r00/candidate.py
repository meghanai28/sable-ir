import sqlite3
import os

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100")
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    tables_query = """
        SELECT name FROM sqlite_master WHERE type='table' AND name=?
    """
    cursor.execute(tables_query, (table_name,))
    table_exists = cursor.fetchone()
    
    if not table_exists:
        raise ValueError(f"Table '{table_name}' does not exist or is not a valid user table")
    
    quoted_table = '"' + table_name.replace('"', '""') + '"'
    
    query = f"SELECT * FROM {quoted_table} ORDER BY rowid LIMIT ?"
    cursor.execute(query, (limit,))
    rows = cursor.fetchall()
    
    conn.close()
    return rows
