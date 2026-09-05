import os
import socket
import urllib.parse
from typing import Tuple, Any, Optional

def fetch_text(url: str, transport: Any, resolve_host: Any) -> str:
    """
    Fetch text from a URL with strict path validation to prevent directory traversal.
    
    Args:
        url: The URL to fetch from.
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of IP addresses.
    
    Returns:
        The body of the response if status is 200.
    
    Raises:
        ValueError: If the request is invalid, path escapes root, or status is not 200.
    """
    # Parse the URL to extract netloc and path
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc
        path = parsed.path
    except Exception:
        raise ValueError("Invalid URL format")

    # Resolve the host
    try:
        ip_addresses = resolve_host(netloc)
        if not ip_addresses:
            raise ValueError("Host resolution failed or returned no IPs")
    except Exception:
        raise ValueError("Failed to resolve host")

    # Determine the scheme and port
    scheme = parsed.scheme.lower()
    if scheme not in ['http', 'https']:
        raise ValueError("Only HTTP and HTTPS schemes are allowed")

    # Determine the default port based on scheme
    default_port = 80 if scheme == 'http' else 443

    # Construct the full URL to pass to transport (including query strings if present)
    # The path component might contain query strings, so we use the full path
    full_url = f"{scheme}://{netloc}{path}"

    # Get the response
    status, headers, body = transport(full_url)

    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")

    # Validate headers and body before returning
    # (Basic check to ensure they are not None or empty in a way that causes issues)
    if body is None or body == "":
        raise ValueError("Response body is empty")

    # Path traversal validation
    # We need to ensure the resolved path does not escape the root.
    # Since the plan mentions "extraction directory", we assume a safe root.
    # However, the prompt implies the URL itself might be a file path or absolute.
    # To be safe and compliant with "normalize and resolve beneath the configured root",
    # we will treat the URL path as the target and ensure it doesn't escape.
    # A robust approach is to resolve the path relative to a safe root (e.g., /) and check.
    
    # Clean the path to remove query strings if they were part of the path string
    # urllib.parse.urlparse splits query, so path is clean.
    # We must ensure the path doesn't start with .. or contain .. that escapes.
    
    # Normalize the path
    # We assume the root is the current directory or a safe base.
    # To strictly follow "beneath the configured root", we'll check if the resolved path starts with '..'
    # or attempts to escape the filesystem root.
    
    # Remove leading slashes to handle absolute paths correctly relative to root
    # But since we are checking for escape, we look at the raw path after normalization.
    # We will use os.path.normpath and check for '..' components that go above root.
    
    # Safely resolve the path
    # We assume the root is the directory where this script runs or a standard safe directory.
    # To be generic, we check if the path starts with '..' or '..' followed by a separator.
    
    # Normalize the path
    normalized_path = os.path.normpath(path)
    
    # Check for directory traversal attempts
    # If the normalized path starts with '..', it's invalid.
    if normalized_path.startswith('..'):
        raise ValueError("Path traversal detected")
    
    # Ensure the path does not contain '..' anywhere that could escape
    # After normpath, if it's absolute, it's fine as long as it doesn't escape the root.
    # If it's relative, it must not escape.
    
    # A more robust check: resolve against a safe root and ensure it stays within.
    # Since no specific root is provided in the function signature, we assume the current working directory
    # is the root, but we must prevent any '..' from escaping the filesystem root (/).
    
    # Check if the path contains '..' that could be problematic before normpath
    # Actually, normpath handles it, but we must ensure the result doesn't escape.
    # If the path is absolute, it might be anywhere. If relative, it's relative to cwd.
    
    # To be safe against any traversal, we ensure the resolved path does not start with '..'
    # and does not contain '..' followed by a separator in a way that escapes.
    
    # Re-check: "Normalize and resolve the requested path beneath the configured root"
    # Since no root is passed, we assume the path is safe if it doesn't traverse up.
    # We check if the path contains '..' which would make normpath return '..' or escape.
    
    if '..' in path:
        # This is a heuristic check, but normpath is the standard.
        # We rely on normpath to clean it, then check if it escapes.
        pass

    # Final validation using os.path.realpath or similar logic if needed,
    # but primarily we ensure no '..' at the start or that leads to escape.
    # The most critical check is that the resolved path does not start with '..'
    # after normalization if it was relative, or if it's absolute, it's fine.
    # However, the prompt says "raise ValueError if the resolved path escapes the root".
    # We assume the root is the current directory.
    
    # Check if the path is absolute and points outside the root (which is impossible on Unix for /)
    # Check if it's relative and escapes.
    
    # We will perform a final check: if the path starts with .. or contains .. in a way that normpath reduces it to escape.
    # Actually, simply checking if the normalized path starts with '..' is sufficient for relative paths.
    # For absolute paths, they are generally safe unless they point to a malicious location,
    # but the constraint is about "escaping the root".
    
    # Let's assume the root is the current working directory.
    # We resolve the path relative to cwd and check.
    
    # Re-evaluating: The prompt says "Treat url as untrusted input... Normalize and resolve... beneath the configured root".
    # Since no root is passed, we assume the path is safe if it doesn't traverse.
    # We check if the path contains '..' which would be dangerous.
    
    if '..' in path or path.startswith('..'):
        raise ValueError("Path traversal detected")

    # If we passed the traversal check, return the body
    return body

# Note: The implementation above focuses on the logic described in the plan.
# It assumes `transport` and `resolve_host` are passed as arguments.
# The function returns the body for status 200 and raises ValueError otherwise.
# Path traversal is checked by ensuring the path does not contain '..' or start with it.
