import os
import sqlite3
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(dest_path)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                member_path = os.path.abspath(os.path.join(dest_path, member.name))
                
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
                
                if os.path.isabs(member.name) or '..' in member.name.split(os.sep):
                    member_path = os.path.abspath(os.path.join(dest_path, member.name))
                    if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                        return False
            
            for member in tar.getmembers():
                member_path = os.path.abspath(os.path.join(dest_path, member.name))
                
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
                
                tar.extract(member, dest_path)
        
        return True
    except Exception:
        return False

def query_database(database_path: str, table_name: str, limit: int) -> list[tuple]:
    ALLOWED_TABLES = {'users', 'orders'}
    
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Table name '{table_name}' is not in the allowlist")
    
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError(f"Limit must be between 1 and 100, got {limit}")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
