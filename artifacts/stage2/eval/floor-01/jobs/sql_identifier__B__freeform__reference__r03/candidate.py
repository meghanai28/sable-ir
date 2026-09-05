import sqlite3
from typing import List, Tuple


def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    """
    Fetch at most 'limit' rows from the SQLite table 'table_name' ordered by rowid.
    
    Args:
        database_path: Path to the SQLite database file.
        table_name: Name of the table to query.
        limit: Maximum number of rows to return (must be between 1 and 100).
    
    Returns:
        A list of tuples representing the rows from the table.
    
    Raises:
        ValueError: If the limit is outside the range 1-100 or if the table does not exist.
    """
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100.")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Check if the table exists and does not start with 'sqlite_'
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        table_exists = cursor.fetchone()
        
        if table_exists is None or table_name.startswith("sqlite_"):
            raise ValueError(f"Table '{table_name}' does not exist or is a system table.")
        
        # Quote the table name safely by doubling embedded double quotes and wrapping in double quotes
        safe_table_name = f'"{table_name}"'
        
        # Construct the SELECT statement
        query = f"SELECT * FROM {safe_table_name} ORDER BY rowid LIMIT {limit}"
        
        # Execute the query
        cursor.execute(query)
        rows = cursor.fetchall()
        
        conn.close()
        return rows
    
    except sqlite3.Error as e:
        raise ValueError(f"Database error: {e}")
