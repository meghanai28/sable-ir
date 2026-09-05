import sqlite3
from typing import List, Tuple


def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    """
    Fetch at most 'limit' rows from 'table_name' in 'database_path' ordered by rowid.
    
    Args:
        database_path: Path to the SQLite database file.
        table_name: Name of the table to query.
        limit: Maximum number of rows to return (must be between 1 and 100).
    
    Returns:
        A list of tuples representing the rows from the table.
    
    Raises:
        ValueError: If 'limit' is not between 1 and 100, or if 'table_name' is invalid.
    """
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100.")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Fetch all tables from sqlite_master
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}
        
        # Check if table_name exists and does not start with sqlite_
        if table_name not in existing_tables or table_name.startswith("sqlite_"):
            raise ValueError(f"Table '{table_name}' does not exist or is a system table.")
        
        # Escape double quotes in table_name
        escaped_table_name = table_name.replace('"', '""')
        query = f'SELECT * FROM "{escaped_table_name}" ORDER BY rowid LIMIT {limit}'
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        conn.close()
        return rows
    
    except sqlite3.Error as e:
        raise ValueError(f"Database error: {e}")
