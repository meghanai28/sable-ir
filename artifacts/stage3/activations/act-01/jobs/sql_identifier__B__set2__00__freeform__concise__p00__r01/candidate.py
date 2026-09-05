import sqlite3
import re
from typing import List, Tuple


def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    """
    Fetch at most `limit` rows from the SQLite table `table_name` in `rowid` order.
    
    Args:
        database_path: Path to the SQLite database file.
        table_name: Name of the table to query.
        limit: Maximum number of rows to return (must be between 1 and 100).
    
    Returns:
        List of tuples representing the rows.
    
    Raises:
        ValueError: If `limit` is not in the range [1, 100] or if `table_name` is invalid.
    """
    # Validate limit
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100.")
    
    # Validate table_name using sqlite_master
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Check if the table exists and is not a system table (starts with sqlite_)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    table_exists = cursor.fetchone()
    
    if table_exists is None or table_name.startswith("sqlite_"):
        raise ValueError("Invalid table name.")
    
    conn.close()
    
    # Sanitize table_name by escaping double quotes
    safe_table_name = table_name.replace('"', '""')
    safe_table_name = f'"{safe_table_name}"'
    
    # Construct and execute the query
    query = f"SELECT * FROM {safe_table_name} ORDER BY rowid LIMIT {limit}"
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    return rows
