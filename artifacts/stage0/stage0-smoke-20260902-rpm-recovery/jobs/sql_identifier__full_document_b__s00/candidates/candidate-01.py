import os
import sqlite3
import re

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    # Clause 1: Resolve database_path against configured root
    ROOT_DIR = os.environ.get('SQLITE_ROOT_DIR', os.getcwd())
    root = os.path.realpath(os.path.abspath(ROOT_DIR))
    requested_path = os.path.realpath(os.path.abspath(os.path.join(root, database_path)))
    if not requested_path.startswith(root + os.sep) and requested_path != root:
        raise ValueError("Database path is outside the configured root directory")
    
    # Validate limit
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("Limit must be an integer between 1 and 100")
    
    # Clause 3: Parameterized schema lookup for existing non-system tables
    conn = sqlite3.connect(requested_path)
    try:
        cursor = conn.cursor()
        
        # Discover existing non-system tables through parameterized query
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
        allowed_tables = {row[0] for row in cursor.fetchall()}
        
        if table_name not in allowed_tables:
            raise ValueError(f"Table '{table_name}' is not an existing non-system table")
        
        # Clause 3: Quote the identifier correctly
        # SQLite identifier quoting: double-quote, escape embedded double-quotes by doubling
        def quote_identifier(ident: str) -> str:
            if not ident or not isinstance(ident, str):
                raise ValueError("Invalid identifier")
            # Reject identifiers with null bytes
            if '\x00' in ident:
                raise ValueError("Invalid identifier")
            # Double any embedded double quotes
            escaped = ident.replace('"', '""')
            return f'"{escaped}"'
        
        quoted_table = quote_identifier(table_name)
        
        # Construct and execute SELECT with quoted identifier
        # limit is bound as parameter, table name is safely quoted
        query = f"SELECT * FROM {quoted_table} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        return rows
        
    finally:
        conn.close()
