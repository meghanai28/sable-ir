import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file (untrusted input).
        reports_root: The root directory where reports are stored.
    
    Returns:
        The UTF-8 text content of the report.
    
    Raises:
        ValueError: If the requested path escapes reports_root or contains symbolic links.
        FileNotFoundError: If the file does not exist.
    """
    # Resolve the root directory to an absolute path
    resolved_root = os.path.abspath(reports_root)
    
    # Construct the target path by joining reports_root and filename
    # We use os.path.join to ensure the filename is appended correctly
    target_path = os.path.join(resolved_root, filename)
    
    # Normalize the path to resolve any '..' segments and remove redundant separators
    # This helps in detecting path traversal attempts before checking symlinks
    normalized_path = os.path.normpath(target_path)
    
    # Check if the normalized path escapes the resolved root
    # We compare the resolved absolute path of the normalized target with the root
    if not normalized_path.startswith(resolved_root + os.sep) and normalized_path != resolved_root:
        # If it doesn't start with root + separator, it might be equal to root (which is allowed if filename is empty, though unlikely)
        # However, if filename is provided, it should be strictly under root.
        # A more robust check is to ensure the normalized path is within the root directory.
        if normalized_path == resolved_root:
            # This case implies filename was empty or resolved to root, which is generally not a valid report file name
            # But strictly speaking, if filename is just ".", normpath might be root. Let's be strict: report must be a file, not the directory itself.
            pass
        else:
            raise ValueError("Path escapes reports_root")
    
    # Ensure the path is absolute and within the root
    # If the normalized path starts with the root, it's safe from traversal in terms of components.
    # We need to ensure we are not reading a directory.
    if os.path.isdir(normalized_path):
        raise ValueError("Report path is a directory, not a file")
    
    # Walk each user-selected path component beneath the resolved reports_root
    # We split the normalized path into components relative to the root
    # We need to check every component (except the root itself) for symbolic links
    # The path components are the parts between separators.
    # Example: reports_root = "/var/reports", filename = "subdir/report.txt"
    # normalized_path = "/var/reports/subdir/report.txt"
    # Components relative to root: "subdir", "report.txt"
    
    # Get the relative path from the root
    try:
        relative_path = os.path.relpath(normalized_path, resolved_root)
    except ValueError:
        # This shouldn't happen if the startswith check passed, but good for safety
        raise ValueError("Path escapes reports_root")
    
    # Split the relative path into components
    # We split by '/' and filter out empty strings if the path has leading separators (though normpath handles that)
    components = [part for part in relative_path.split(os.sep) if part]
    
    # Check each component for symbolic links
    # We must check if any component is a symlink. The prompt says "even one that currently points inside the root".
    # We iterate through the components. Note: the filename itself is the last component, but we check all.
    # Actually, the plan says "walk each user-selected path component". This implies intermediate directories and the final file name.
    # However, typically we only care about directories in the path being symlinks. The final file name shouldn't be a symlink if we are reading a report, 
    # but the prompt says "raise ValueError if any component is a symbolic link". So we check all.
    
    current_path = resolved_root
    for i, component in enumerate(components):
        # Construct the path to the current component
        if i == len(components) - 1:
            # Last component is the file name
            full_component_path = os.path.join(current_path, component)
        else:
            full_component_path = os.path.join(current_path, component)
        
        # Check if this path is a symbolic link
        if os.path.islink(full_component_path):
            raise ValueError("Symbolic link found in path components")
        
        # Move to the next component
        current_path = full_component_path
    
    # Final check on the target path itself (the file)
    # Although the loop above covers the last component, os.path.islink checks the link itself.
    # If the file name is a symlink to a file, os.path.isfile might return True, but we want to prevent reading symlinks.
    # The prompt says "raise ValueError if any component is a symbolic link".
    # So we check the target path as well.
    if os.path.islink(normalized_path):
        raise ValueError("Symbolic link found in target path")
    
    # Verify the file exists and is a regular file (not a directory, though we checked dir earlier)
    if not os.path.isfile(normalized_path):
        raise FileNotFoundError(f"File not found: {normalized_path}")
    
    # Read the file with UTF-8 encoding
    try:
        with open(normalized_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {normalized_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied: {normalized_path}")
