import os


def read_report(filename: str, reports_root: str) -> str:
    # Resolve the absolute path of reports_root
    abs_reports_root = os.path.abspath(reports_root)
    
    # Join filename with reports_root and get absolute path
    requested_path = os.path.join(abs_reports_root, filename)
    abs_requested_path = os.path.abspath(requested_path)
    
    # Fully resolve symlinks to get the real path
    try:
        real_path = os.path.realpath(abs_requested_path)
    except OSError:
        raise ValueError("Path resolution failed")
    
    # Verify the final target remains inside reports_root
    # Use commonpath for proper prefix checking to avoid path traversal
    try:
        common = os.path.commonpath([real_path, abs_reports_root])
    except ValueError:
        # On Windows, commonpath raises ValueError for different drives
        raise ValueError("Path escapes approved root")
    
    if common != abs_reports_root:
        raise ValueError("Path escapes approved root")
    
    # Verify the target is an ordinary file
    if not os.path.isfile(real_path):
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"No such file: {real_path}")
        raise ValueError("Not an ordinary file")
    
    # Read and decode as UTF-8
    with open(real_path, 'r', encoding='utf-8') as f:
        return f.read()
