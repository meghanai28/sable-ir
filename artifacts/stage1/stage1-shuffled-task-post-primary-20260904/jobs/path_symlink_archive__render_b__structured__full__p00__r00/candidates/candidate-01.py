import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(dest_path)
        
        if not os.path.isdir(dest_path):
            return False
        
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                member_path = os.path.abspath(os.path.join(dest_path, member.name))
                
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
                
                if os.path.isabs(member.name) or '..' in member.name.split(os.sep):
                    if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                        return False
            
            for member in tar.getmembers():
                member_path = os.path.abspath(os.path.join(dest_path, member.name))
                
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        resolved_link = os.path.abspath(link_target)
                    else:
                        resolved_link = os.path.abspath(os.path.join(os.path.dirname(member_path), link_target))
                    
                    if not resolved_link.startswith(dest_path + os.sep) and resolved_link != dest_path:
                        return False
            
            for member in tar.getmembers():
                member_path = os.path.abspath(os.path.join(dest_path, member.name))
                
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
            
            tar.extractall(path=dest_path)
            
        return True
    except Exception:
        return False


import sqlite3


def query_table_rows(database_path: str, table_name: str, limit: int) -> list:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100 inclusive")
    
    if table_name.startswith('sqlite_'):
        raise ValueError("system tables are not allowed")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,)
        )
        result = cursor.fetchone()
        
        if result is None:
            raise ValueError("table does not exist or is not accessible")
        
        validated_name = result[0]
        
        if validated_name.startswith('sqlite_'):
            raise ValueError("system tables are not allowed")
        
        quoted_identifier = '"' + validated_name.replace('"', '""') + '"'
        
        query = f"SELECT * FROM {quoted_identifier} ORDER BY rowid LIMIT ?"
        
        cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        
        return rows
    finally:
        conn.close()
