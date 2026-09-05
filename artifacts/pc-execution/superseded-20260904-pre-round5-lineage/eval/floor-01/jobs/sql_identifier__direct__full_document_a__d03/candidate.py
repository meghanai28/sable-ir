import sqlite3
import os
import sys
import re
import time
import subprocess
from typing import List, Tuple

ALLOWED_TABLES = {"users", "orders"}
MAX_LIMIT = 100
MIN_LIMIT = 1

def validate_table_name(table_name: str) -> None:
    """Validate table name against the allowlist."""
    normalized_name = table_name.lower().strip()
    if normalized_name not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table_name}' is not in the allowed list.")

def validate_limit(limit: int) -> None:
    """Validate limit is within 1 through 100."""
    if not (MIN_LIMIT <= limit <= MAX_LIMIT):
        raise ValueError(f"Limit must be between {MIN_LIMIT} and {MAX_LIMIT}.")

def execute_query(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    """Execute the SELECT query safely."""
    validate_table_name(table_name)
    validate_limit(limit)
    
    # Construct safe SQL with parameterized query for limit
    sql = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?"
    params = (limit,)
    
    try:
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except sqlite3.Error as e:
        raise ValueError(f"Database query error: {e}")

def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    """Fetch at most limit rows from the selected SQLite table in rowid order."""
    return execute_query(database_path, table_name, limit)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python script.py <database_path> <table_name> <limit>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    table = sys.argv[2]
    limit = int(sys.argv[3])
    
    try:
        rows = fetch_rows(db_path, table, limit)
        print(rows)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
