import os
import sys

def read_report(filename: str, reports_root: str) -> str:
    """
    Read and return the requested UTF-8 report beneath reports_root.
    
    Args:
        filename: The name of the report file to read.
        reports_root: The root directory where reports are stored.
    
    Returns:
        The UTF-8 text content of the report.
    
    Raises:
        FileNotFoundError: If the file does not exist or is not an ordinary file.
        ValueError: If the requested path escapes the reports_root or if a symbolic link points outside.
    """
    # Resolve the absolute path for reports_root
    resolved_root = os.path.abspath(reports_root)
    
    # Resolve the absolute path for the requested filename
    resolved_filename = os.path.abspath(filename)
    
    # Construct the full path
    full_path = os.path.join(resolved_root, resolved_filename)
    
    # Normalize the path to remove any redundant separators or current directory references
    # This helps in validating containment correctly
    normalized_full_path = os.path.normpath(full_path)
    
    # Validate that the normalized path is within the reports_root
    # We use os.path.commonpath to ensure the path is strictly within the root
    try:
        common_path = os.path.commonpath([resolved_root, normalized_full_path])
        if common_path != resolved_root:
            raise ValueError("Path escapes reports_root")
    except ValueError:
        raise ValueError("Path escapes reports_root")
    
    # Check if the file exists and is an ordinary file (not a directory or symlink)
    # Note: os.path.isfile follows symlinks, but we need to check the target specifically
    if not os.path.isfile(normalized_full_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Additional check: if the file is a symlink, resolve its target and ensure it's within reports_root
    # os.path.isfile returns True for symlinks pointing to files, but we need to be careful about the target
    if os.path.islink(normalized_full_path):
        # Resolve the target of the symlink
        link_target = os.path.realpath(normalized_full_path)
        # Ensure the resolved target is within reports_root
        try:
            common_path = os.path.commonpath([resolved_root, link_target])
            if common_path != resolved_root:
                raise ValueError("Symbolic link escapes reports_root")
        except ValueError:
            raise ValueError("Symbolic link escapes reports_root")
    
    # Read the file content
    try:
        with open(normalized_full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filename}")

# Register the function for import
if __name__ == "__main__":
    import importlib
    importlib.reload(sys.modules[__name__])
