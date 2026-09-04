import sqlite3
import re
import os.path

def _is_valid_table_name(table_name: str) -> bool:
    if not table_name:
        return False
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', table_name):
        return False
    reserved_keywords = {
        'ABORT', 'ACTION', 'ADD', 'AFTER', 'ALL', 'ALTER', 'ANALYZE', 'AND', 'AS', 'ASC',
        'ATTACH', 'AUTOINCREMENT', 'BEFORE', 'BEGIN', 'BETWEEN', 'BY', 'CASCADE', 'CASE',
        'CAST', 'CHECK', 'COLLATE', 'COLUMN', 'COMMIT', 'CONFLICT', 'CONSTRAINT', 'CREATE',
        'CROSS', 'CURRENT_DATE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP', 'DATABASE', 'DEFAULT',
        'DEFERRABLE', 'DEFERRED', 'DELETE', 'DESC', 'DETACH', 'DISTINCT', 'DROP', 'EACH',
        'ELSE', 'END', 'ESCAPE', 'EXCEPT', 'EXCLUSIVE', 'EXISTS', 'EXPLAIN', 'FAIL', 'FOR',
        'FOREIGN', 'FROM', 'FULL', 'GLOB', 'GROUP', 'HAVING', 'IF', 'IGNORE', 'IMMEDIATE',
        'IN', 'INDEX', 'INDEXED', 'INITIALLY', 'INNER', 'INSERT', 'INSTEAD', 'INTERSECT',
        'INTO', 'IS', 'ISNULL', 'JOIN', 'KEY', 'LEFT', 'LIKE', 'LIMIT', 'MATCH', 'NATURAL',
        'NO', 'NOT', 'NOTNULL', 'NULL', 'OF', 'OFFSET', 'ON', 'OR', 'ORDER', 'OUTER', 'PLAN',
        'PRAGMA', 'PRIMARY', 'QUERY', 'RAISE', 'RECURSIVE', 'REFERENCES', 'REGEXP', 'REINDEX',
        'RELEASE', 'RENAME', 'REPLACE', 'RESTRICT', 'RIGHT', 'ROLLBACK', 'ROW', 'SAVEPOINT',
        'SELECT', 'SET', 'TABLE', 'TEMP', 'TEMPORARY', 'THEN', 'TO', 'TRANSACTION', 'TRIGGER',
        'UNION', 'UNIQUE', 'UPDATE', 'USING', 'VACUUM', 'VALUES', 'VIEW', 'VIRTUAL', 'WHEN',
        'WHERE', 'WITH', 'WITHOUT'
    }
    if table_name.upper() in reserved_keywords:
        return False
    return True

def _normalize_archive_member(member_name: str, extraction_dir: str) -> str:
    normalized = os.path.normpath(member_name)
    if normalized.startswith(os.sep):
        normalized = normalized.lstrip(os.sep)
    if os.path.isabs(member_name):
        raise ValueError("Archive member path must be relative")
    resolved = os.path.join(extraction_dir, normalized)
    resolved = os.path.normpath(resolved)
    real_extract = os.path.realpath(extraction_dir)
    real_resolved = os.path.realpath(resolved)
    if not real_resolved.startswith(real_extract + os.sep) and real_resolved != real_extract:
        raise ValueError("Archive member escapes extraction directory")
    return resolved

def _is_special_entry(member_name: str) -> bool:
    import stat
    try:
        st = os.lstat(member_name)
        mode = st.st_mode
        if stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode):
            return True
    except (OSError, FileNotFoundError):
        pass
    return False

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100 inclusive")
    
    if not _is_valid_table_name(table_name):
        raise ValueError("disallowed table name")
    
    extraction_dir = os.path.dirname(os.path.abspath(database_path)) or os.getcwd()
    
    if _is_special_entry(database_path):
        raise ValueError("database path is a special entry")
    
    normalized_db = _normalize_archive_member(os.path.basename(database_path), extraction_dir)
    
    if not os.path.exists(normalized_db):
        pass
    
    conn = sqlite3.connect(normalized_db)
    try:
        cursor = conn.cursor()
        
        query = f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?"
        
        cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        
        return rows
    finally:
        conn.close()
