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
                    return False
            for member in tar.getmembers():
                member_path = os.path.abspath(os.path.join(dest_path, member.name))
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        return False
                    resolved_link = os.path.normpath(os.path.join(os.path.dirname(member_path), link_target))
                    if not resolved_link.startswith(dest_path + os.sep) and resolved_link != dest_path:
                        return False
            tar.extractall(path=dest_path)
        return True
    except (tarfile.TarError, OSError, ValueError):
        return False


def query_table(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        if table_name not in existing_tables:
            raise ValueError(f"table_name '{table_name}' is not an existing non-system table")
        
        quoted_table = '"' + table_name.replace('"', '""') + '"'
        
        query = f"SELECT * FROM {quoted_table} ORDER BY rowid LIMIT ?"
        cursor.execute(query, (limit,))
        
        results = cursor.fetchall()
        return results
    finally:
        conn.close()
