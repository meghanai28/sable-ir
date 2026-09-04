import sqlite3
import os
import re
import zipfile
import tarfile
import stat

def _normalize_archive_member_name(name: str) -> str:
    name = name.replace('\\', '/')
    while name.startswith('/'):
        name = name[1:]
    while '../' in name:
        name = name.replace('../', '')
    if name.startswith('..'):
        name = name[2:]
    while './' in name:
        name = name.replace('./', '')
    return name

def _is_within_extraction_dir(member_path: str, extraction_dir: str) -> bool:
    abs_member = os.path.abspath(os.path.join(extraction_dir, member_path))
    abs_extraction = os.path.abspath(extraction_dir)
    return abs_member.startswith(abs_extraction + os.sep) or abs_member == abs_extraction

def _is_special_entry(info) -> bool:
    if isinstance(info, zipfile.ZipInfo):
        mode = info.external_attr >> 16
        return stat.S_ISBLK(mode) or stat.S_ISCHR(mode) or stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode)
    elif isinstance(info, tarfile.TarInfo):
        return info.isblk() or info.ischr() or info.isfifo() or info.issock() or info.isdev()
    return False

def _validate_archive_members(archive_path: str, extraction_dir: str) -> None:
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path, 'r') as zf:
            for info in zf.infolist():
                normalized = _normalize_archive_member_name(info.filename)
                if not normalized:
                    continue
                if not _is_within_extraction_dir(normalized, extraction_dir):
                    raise ValueError(f"Member {info.filename} extracts outside target directory")
                if _is_special_entry(info):
                    raise ValueError(f"Member {info.filename} is a special entry")
    elif tarfile.is_tarfile(archive_path):
        with tarfile.TarFile(archive_path, 'r') as tf:
            for info in tf.getmembers():
                normalized = _normalize_archive_member_name(info.name)
                if not normalized:
                    continue
                if not _is_within_extraction_dir(normalized, extraction_dir):
                    raise ValueError(f"Member {info.name} extracts outside target directory")
                if _is_special_entry(info):
                    raise ValueError(f"Member {info.name} is a special entry")
    else:
        raise ValueError(f"Unsupported archive format: {archive_path}")

def fetch_rows(database_path: str, table_name: str, limit: int) -> list[tuple]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100 inclusive")
    
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', table_name):
        raise ValueError(f"disallowed table name: {table_name}")
    
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY rowid LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
