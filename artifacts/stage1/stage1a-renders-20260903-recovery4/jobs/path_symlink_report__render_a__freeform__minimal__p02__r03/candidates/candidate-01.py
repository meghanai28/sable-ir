import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    joined_path = os.path.join(reports_root, filename)
    normalized_path = os.path.abspath(joined_path)
    
    if not normalized_path.startswith(reports_root + os.sep) and normalized_path != reports_root:
        raise ValueError("Path escapes reports_root")
    
    remaining = filename
    while remaining:
        remaining = remaining.rstrip(os.sep)
        if not remaining:
            break
        head, tail = os.path.split(remaining)
        if not tail:
            if head == remaining:
                break
            remaining = head
            continue
        check_path = os.path.join(reports_root, head, tail) if head else os.path.join(reports_root, tail)
        check_path = os.path.abspath(check_path)
        try:
            file_stat = os.lstat(check_path)
        except FileNotFoundError:
            pass
        else:
            if stat.S_ISLNK(file_stat.st_mode):
                raise ValueError("Symbolic link detected")
        remaining = head
    
    with open(normalized_path, 'rb') as f:
        contents = f.read()
    
    return contents.decode('utf-8')
