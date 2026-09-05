import os
import stat
import pathlib

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: Untrusted input filename to read.
        reports_root: Root directory where reports are stored.
    
    Returns:
        The content of the report file as a UTF-8 string.
    
    Raises:
        FileNotFoundError: If the file does not exist or is not a regular file.
        ValueError: If the path escapes reports_root or contains symbolic links.
    """
    root_path = pathlib.Path(reports_root).resolve()
    requested_path = pathlib.Path(filename).resolve()
    
    # Check if filename is absolute and escapes root
    if requested_path.is_absolute():
        if not requested_path.anchor.startswith('/'):
            # On Unix, absolute paths start with /; on Windows, they start with drive letter
            # We need to ensure the resolved path is still within root
            pass
    
    # Normalize the requested path to be relative to reports_root for validation
    # First, make sure we're working with the correct base
    base = root_path
    requested_relative = requested_path.relative_to(base) if requested_path.is_relative_to(base) else None
    
    # If the path is absolute and not under root, or cannot be made relative, it escapes
    if not requested_relative:
        raise ValueError("Requested path escapes reports_root")
    
    # Normalize the path to remove any .. segments that might have been in the input
    # We need to resolve the path but then check if it's still within root
    normalized_path = requested_relative.resolve()
    
    # Check if the normalized path is still within the root
    if not normalized_path.is_relative_to(base):
        raise ValueError("Requested path escapes reports_root")
    
    # Check each component of the path for symbolic links
    parts = normalized_path.parts
    current_path = base
    
    for part in parts:
        next_path = current_path / part
        
        # Check if any component is a symbolic link
        if next_path.is_symlink():
            raise ValueError("Symbolic link detected in path")
        
        # Also check if the symlink target would escape (though the prompt says 
        # "even one that currently points inside reports_root" is dangerous, 
        # so we block the link itself regardless of target)
        current_path = next_path
    
    # Now that we've validated the path, check if the file exists and is a regular file
    if not normalized_path.exists():
        raise FileNotFoundError(f"File not found: {normalized_path}")
    
    if not normalized_path.is_file():
        raise FileNotFoundError(f"Not a regular file: {normalized_path}")
    
    # Read and return the file content
    with open(normalized_path, 'r', encoding='utf-8') as f:
        return f.read()
