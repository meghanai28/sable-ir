import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Safety checks applied:
    1. Ensures the resolved path is within the approved filesystem root.
    2. Rejects symbolic links that resolve outside the root or point to special files.
    3. Propagates FileNotFoundError for missing ordinary files.
    4. Raises ValueError when the request is disallowed (e.g., path outside root).
    """
    # Resolve the absolute path for the requested file
    try:
        target_path = os.path.abspath(filename)
    except (ValueError, TypeError):
        raise ValueError("Invalid filename provided")

    # Ensure the target is within the approved root
    root_path = os.path.abspath(reports_root)
    
    # If the target is not under the root, raise ValueError
    if not target_path.startswith(root_path + os.sep) and target_path != root_path:
        raise ValueError("Access denied: file path is outside the approved root")

    # Check if the file exists
    if not os.path.isfile(target_path):
        raise FileNotFoundError(f"The file '{filename}' does not exist")

    # Check for symbolic links and resolve them
    if os.path.islink(target_path):
        # Resolve the symlink target
        link_target = os.path.realpath(target_path)
        
        # Ensure the resolved target is still within the root
        if not link_target.startswith(root_path + os.sep) and link_target != root_path:
            raise ValueError("Access denied: symlink resolves outside the approved root")
        
        # Check if the resolved target is a special file (e.g., device, socket, pipe)
        try:
            file_stat = os.stat(link_target)
            if not (file_stat.st_mode & stat.S_IFREG):
                raise ValueError("Access denied: symlink points to a non-regular file")
        except OSError:
            raise ValueError("Access denied: symlink target is inaccessible or invalid")

    # If the file is a symlink to itself or a directory, raise an error
    if os.path.islink(target_path) and not os.path.isfile(target_path):
        raise ValueError("Access denied: symlink does not point to a regular file")

    # Read the file content
    try:
        with open(target_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise
    except Exception as e:
        raise ValueError(f"Error reading file: {str(e)}") from e
