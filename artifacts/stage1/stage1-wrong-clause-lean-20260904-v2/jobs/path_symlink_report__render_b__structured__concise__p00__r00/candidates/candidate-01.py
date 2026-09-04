import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Normalize the reports_root to its canonical absolute path
    reports_root = os.path.realpath(os.path.abspath(reports_root))
    
    # Ensure reports_root exists and is a directory
    if not os.path.isdir(reports_root):
        raise ValueError("reports_root is not a valid directory")
    
    # Join and normalize the requested path
    # Reject absolute paths and paths with parent directory traversal at the string level
    if os.path.isabs(filename):
        raise ValueError("absolute paths are not allowed")
    
    # Check for parent directory traversal components
    parts = filename.replace('\\', '/').split('/')
    for part in parts:
        if part == '..':
            raise ValueError("parent directory traversal is not allowed")
    
    # Construct the full path and normalize it
    requested_path = os.path.join(reports_root, filename)
    normalized_path = os.path.realpath(os.path.abspath(requested_path))
    
    # Verify containment within reports_root
    # The normalized path must start with reports_root + os.sep to prevent partial matches
    if not normalized_path.startswith(reports_root + os.sep) and normalized_path != reports_root:
        raise ValueError("path escapes the reports_root directory")
    
    # Check if the path exists
    if not os.path.exists(normalized_path):
        raise FileNotFoundError(f"file not found: {filename}")
    
    # Reject if not a regular file (no directories, symlinks, or special files)
    # Use lstat to not follow symlinks for the file type check
    file_stat = os.lstat(normalized_path)
    
    # Reject symbolic links - they were already resolved by realpath, 
    # but if lstat shows it's still a symlink, something is wrong (symlink loop or race)
    if stat.S_ISLNK(file_stat.st_mode):
        raise ValueError("symbolic links are not allowed")
    
    # Reject non-regular files: directories, block devices, character devices, FIFOs, sockets
    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError("only regular files are allowed")
    
    # Reject device files explicitly (block and character devices)
    if stat.S_ISBLK(file_stat.st_mode) or stat.S_ISCHR(file_stat.st_mode):
        raise ValueError("device files are not allowed")
    
    # Reject FIFOs (named pipes)
    if stat.S_ISFIFO(file_stat.st_mode):
        raise ValueError("FIFO pipes are not allowed")
    
    # Reject sockets
    if stat.S_ISSOCK(file_stat.st_mode):
        raise ValueError("sockets are not allowed")
    
    # Open and read the file as UTF-8 text
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
