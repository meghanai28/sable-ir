import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Canonicalize reports_root to an absolute path
    abs_reports_root = os.path.abspath(os.path.realpath(reports_root))
    
    # Ensure reports_root exists and is a directory
    if not os.path.isdir(abs_reports_root):
        raise ValueError("reports_root must be a directory")
    
    # Combine root with filename using OS path join semantics
    # Prevent absolute filename from overriding root by making it relative first
    if os.path.isabs(filename):
        # Strip leading separators to make it relative
        filename = filename.lstrip(os.sep)
        # Handle Windows-style absolute paths
        if os.path.isabs(filename):
            # Has drive letter or UNC, strip further
            if len(filename) >= 2 and filename[1] == ':':
                filename = filename[2:].lstrip(os.sep)
            elif filename.startswith('\\\\'):
                # UNC path, find next separator after share
                parts = filename[2:].split(os.sep, 2)
                if len(parts) >= 3:
                    filename = parts[2]
                else:
                    filename = ''
    
    # Join with the root
    combined_path = os.path.join(abs_reports_root, filename)
    
    # Resolve the path to handle any symlinks and traversal sequences
    try:
        resolved_path = os.path.realpath(combined_path)
    except (OSError, ValueError):
        raise ValueError("Invalid path")
    
    # Validate the resolved path is strictly beneath reports_root
    # Use path-boundary-aware comparison
    # Ensure resolved_path is not equal to reports_root and is a proper subpath
    if resolved_path == abs_reports_root:
        raise ValueError("Path must be strictly beneath reports_root")
    
    # Check that resolved_path starts with abs_reports_root followed by separator
    # This prevents partial directory name matches
    if not resolved_path.startswith(abs_reports_root + os.sep):
        raise ValueError("Path escapes the destination directory")
    
    # Check if the path exists to determine file type
    # If it doesn't exist, we still need to validate what type of file it would be
    # But we can only check lstat if it exists
    try:
        file_stat = os.lstat(resolved_path)
    except FileNotFoundError:
        # File doesn't exist, but we need to check if it's a symlink that points outside
        # Check if any component is a symlink with bad target
        # Also need to verify the path doesn't contain special components
        # Since it doesn't exist, we can't stat it, so we allow FileNotFoundError to propagate
        # But first, check parent directories for symlinks that escape
        current = resolved_path
        while current != abs_reports_root:
            parent = os.path.dirname(current)
            if parent == current:
                break
            try:
                parent_stat = os.lstat(parent)
                if stat.S_ISLNK(parent_stat.st_mode):
                    parent_target = os.readlink(parent)
                    if not os.path.isabs(parent_target):
                        parent_target = os.path.join(os.path.dirname(parent), parent_target)
                    parent_resolved = os.path.realpath(parent_target)
                    if not parent_resolved.startswith(abs_reports_root + os.sep) and parent_resolved != abs_reports_root:
                        raise ValueError("Symlink target escapes destination directory")
            except FileNotFoundError:
                pass
            current = parent
        
        # Validate the final path component isn't trying to be a special file by name
        # Since it doesn't exist, we can't determine file type
        # Open it and let FileNotFoundError propagate
        with open(resolved_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # Check for special entries: device files, FIFOs, sockets, directories
    mode = file_stat.st_mode
    
    # Reject if not a regular file (and not a symlink, which realpath already resolved)
    if stat.S_ISDIR(mode):
        raise ValueError("Directories are not allowed")
    if stat.S_ISCHR(mode) or stat.S_ISBLK(mode):
        raise ValueError("Device files are not allowed")
    if stat.S_ISFIFO(mode):
        raise ValueError("FIFOs are not allowed")
    if stat.S_ISSOCK(mode):
        raise ValueError("Sockets are not allowed")
    if stat.S_ISLNK(mode):
        # This shouldn't happen after realpath, but check anyway
        # Verify symlink target is within bounds
        link_target = os.readlink(resolved_path)
        if not os.path.isabs(link_target):
            link_target = os.path.join(os.path.dirname(resolved_path), link_target)
        link_resolved = os.path.realpath(link_target)
        if not link_resolved.startswith(abs_reports_root + os.sep) and link_resolved != abs_reports_root:
            raise ValueError("Symlink target escapes destination directory")
        # Re-check the target
        try:
            target_stat = os.stat(link_resolved)
            target_mode = target_stat.st_mode
            if not stat.S_ISREG(target_mode):
                raise ValueError("Symlink target is not an ordinary file")
        except FileNotFoundError:
            raise ValueError("Symlink target does not exist")
        # Replace resolved_path with link target for reading
        resolved_path = link_resolved
    
    if not stat.S_ISREG(mode):
        raise ValueError("Only ordinary files are allowed")
    
    # All validations passed, open and read the file
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()
