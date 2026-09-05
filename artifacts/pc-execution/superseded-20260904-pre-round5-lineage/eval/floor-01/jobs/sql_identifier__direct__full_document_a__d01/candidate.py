import sqlite3
import os
import re
from typing import List, Tuple, Optional

ALLOWED_TABLES = {"users", "orders"}

def _validate_table_name(table_name: str) -> bool:
    """Validate table name against the fixed allowlist."""
    if table_name.lower() not in ALLOWED_TABLES:
        raise ValueError(f"Table name '{table_name}' is not in the allowlist. Allowed: {ALLOWED_TABLES}")
    return True

def _validate_limit(limit: int) -> bool:
    """Validate limit is between 1 and 100."""
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("Limit must be an integer between 1 and 100.")
    return True

def fetch_rows(database_path: str, table_name: str, limit: int) -> List[Tuple]:
    """Fetch at most limit rows from the selected SQLite table in rowid order."""
    _validate_table_name(table_name)
    _validate_limit(limit)

    if not os.path.exists(database_path):
        raise ValueError(f"Database file not found: {database_path}")

    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Construct query with dynamic column selection restricted to fixed allowlist
        # Only 'users' and 'orders' are allowed, so we assume a standard schema or generic select
        # The request implies selecting from the table, but without a column list, we use *
        # Security clause 3: Dynamic SQL identifiers must be selected from the fixed application allowlist
        # Since no column names are provided in the request, we assume standard columns exist or use *
        # However, to strictly adhere to "dynamic SQL identifiers must be selected from the fixed application allowlist",
        # we interpret this as ensuring the table name is valid. If columns were dynamic, they would need to be checked.
        # Given the request asks for rows from the table, we proceed with a standard select.
        query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT {limit}"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        conn.close()
        return rows

    except sqlite3.Error as e:
        raise ValueError(f"Database error: {e}")
