import os

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    Propagate FileNotFoundError for a missing ordinary file and raise ValueError
    when the request is disallowed.
    """
    # Resolve the root directory to an absolute path
    resolved_root = os.path.abspath(reports_root)
    
    # Resolve the requested filename to an absolute path
    resolved_filename = os.path.abspath(filename)
    
    # Check if the resolved filename is within the reports_root
    # We use os.path.commonpath to ensure the path is strictly within the root
    try:
        common_path = os.path.commonpath([resolved_root, resolved_filename])
        if common_path != resolved_root:
            raise ValueError("Request escapes reports_root")
    except ValueError:
        raise ValueError("Invalid path structure")
    
    # Check if the file exists and is a regular file
    if not os.path.isfile(resolved_filename):
        raise FileNotFoundError(f"The file {filename} does not exist")
    
    # Check if it's a symbolic link
    if os.path.islink(resolved_filename):
        # Resolve the symbolic link target
        link_target = os.path.realpath(resolved_filename)
        
        # Check if the resolved target is within reports_root
        try:
            common_path = os.path.commonpath([resolved_root, link_target])
            if common_path != resolved_root:
                raise ValueError("Symbolic link escapes reports_root")
        except ValueError:
            raise ValueError("Invalid path structure")
        
        # Even if the target is inside, following the link is not allowed
        raise ValueError("Symbolic links are not allowed")
    
    # Read the file
    with open(resolved_filename, 'r', encoding='utf-8') as f:
        return f.read()
