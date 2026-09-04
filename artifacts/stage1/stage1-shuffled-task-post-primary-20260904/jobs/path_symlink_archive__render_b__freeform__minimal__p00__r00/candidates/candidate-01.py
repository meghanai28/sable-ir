import os
import tarfile
from typing import List, Tuple

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        real_dest = os.path.realpath(dest_path)
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf.getmembers():
                member_path = os.path.join(real_dest, member.name)
                real_member_path = os.path.realpath(member_path)
                if not real_member_path.startswith(real_dest + os.sep) and real_member_path != real_dest:
                    return False
                if os.path.isabs(member.name) or '..' in member.name.split(os.sep):
                    # Additional safety check for path traversal in member names
                    pass  # realpath check above handles this, but we keep structure
            tf.extractall(path=dest_path)
        return True
    except Exception:
        return False

import sqlite3

def get_table_rows(db_path: str, table_name: str, limit: int) -> List[Tuple]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100 inclusive")
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        # Parameterized schema lookup for existing non-system tables
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        if table_name not in existing_tables:
            raise ValueError(f"table_name '{table_name}' does not match an existing non-system table")
        
        # Quote table_name correctly as a SQL identifier
        # SQLite identifier quoting: double quotes, escape inner double quotes by doubling
        quoted_table = '"' + table_name.replace('"', '""') + '"'
        
        # Construct SELECT with quoted identifier and parameterized LIMIT
        query = f"SELECT * FROM {quoted_table} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
