import sqlite3
from typing import List, Tuple


def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    """
    Fetch at most 'limit' rows from the specified SQLite table ordered by rowid.
    
    Args:
        database_path: Path to the SQLite database file.
        table_name: Name of the table to query (must be 'users' or 'orders').
        limit: Maximum number of rows to return (must be between 1 and 100).
    
    Returns:
        List of tuples representing the rows from the table.
    
    Raises:
        ValueError: If table_name is not 'users' or 'orders', or if limit is outside 1-100.
    """
    allowed_tables = {'users', 'orders'}
    
    if table_name not in allowed_tables:
        raise ValueError(f"Disallowed table name: {table_name}")
    
    if not (1 <= limit <= 100):
        raise ValueError(f"Limit must be between 1 and 100, got {limit}")
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT {limit}"
    cursor.execute(query)
    rows = cursor.fetchall()
    
    conn.close()
    return rows
