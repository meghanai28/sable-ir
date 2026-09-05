import urllib.request
import urllib.parse
import urllib.error
import os
import socket
import fnmatch
import posixpath

def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with path traversal and symlink protection.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): Function that returns (status, headers, body) tuple.
        resolve_host (callable): Function that resolves hostname to IP addresses.
    
    Returns:
        str: The body of the response for status 200.
    
    Raises:
        ValueError: If the request is disallowed (e.g., path escapes directory).
    """
    # Extract the path component from the URL
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    
    if not path:
        path = "/"
    
    # Define the extraction directory (default to current working directory if not specified, 
    # but per plan "SINK: opening and reading a file on the filesystem", we need a base.
    # Since the plan mentions "extraction directory" but the input doesn't explicitly provide it,
    # we assume the base is the directory containing the script or a configurable base.
    # However, to strictly follow "GUARD: normalize the requested path beneath the selected extraction directory",
    # we must have a base. Let's assume a default base of the current working directory for this implementation
    # or raise an error if not provided. Given the strict plan, we'll use the current working directory as the base.
    # If a specific base is intended to be passed, it should be added to the function signature, but based on the prompt,
    # we proceed with a base directory. Let's assume the base is the directory where the script is run or a fixed base.
    # To be safe and compliant with "SINK: opening and reading a file on the filesystem", we need a base.
    # Let's define a BASE_DIR. If the environment expects a specific base, it should be passed.
    # Since the prompt says "selected extraction directory", and it's not in args, we'll use the current working directory.
    base_dir = os.getcwd()
    
    # Normalize the path to prevent ../ traversal
    # Remove leading slashes and normalize
    normalized_path = posixpath.normpath(path)
    
    # Ensure the path doesn't start with ..
    if normalized_path.startswith('..'):
        raise ValueError("Path traversal detected")
    
    # Construct the full path
    full_path = os.path.join(base_dir, normalized_path)
    
    # Normalize the full path to resolve any remaining .. or .
    # Also, handle the case where the path is absolute
    if os.path.isabs(full_path):
        # If absolute, check if it's within base_dir (shouldn't be if base_dir is cwd, but good to check)
        # Actually, if the URL is absolute path, we might need to handle it differently.
        # But typically, web URLs are relative or have scheme.
        # Let's assume the path is relative to base_dir.
        pass
    
    # Check if the path escapes the base directory
    # Normalize base_dir to absolute
    abs_base_dir = os.path.abspath(base_dir)
    abs_full_path = os.path.abspath(full_path)
    
    if not abs_full_path.startswith(abs_base_dir + os.sep) and abs_full_path != abs_base_dir:
        raise ValueError("Path escapes extraction directory")
    
    # Resolve symbolic links
    try:
        resolved_path = os.path.realpath(full_path)
    except (OSError, ValueError):
        raise ValueError("Could not resolve path")
    
    # Check if the resolved path is within the base directory
    if not resolved_path.startswith(abs_base_dir + os.sep) and resolved_path != abs_base_dir:
        raise ValueError("Resolved path escapes extraction directory")
    
    # Now fetch the content
    try:
        response = transport(url)
        status, headers, body = response
        
        if status != 200:
            raise ValueError(f"Status code {status} is not 200")
        
        # Return the body
        if isinstance(body, bytes):
            return body.decode('utf-8')
        else:
            return body
            
    except Exception as e:
        raise ValueError(f"Request failed: {str(e)}")
