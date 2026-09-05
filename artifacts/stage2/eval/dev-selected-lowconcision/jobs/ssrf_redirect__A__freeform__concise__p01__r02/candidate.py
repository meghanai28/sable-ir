import urllib.parse
import urllib.request
import urllib.error
import socket
import os
import re
from typing import Tuple, List, Union

def fetch_text(url: str, transport, resolve_host: callable) -> str:
    """
    Fetches text from a URL after validating it is safe relative to a root.
    
    Args:
        url: The URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the request is disallowed (e.g., status != 200, path escapes root).
    """
    # Configuration: Assume root is the current working directory for this implementation
    # In a real scenario, this might be a configurable constant.
    ROOT_DIR = os.getcwd()
    
    # 1. Parse the URL
    parsed_url = urllib.parse.urlparse(url)
    
    # 2. Resolve hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    if not ip_addresses:
        raise ValueError(f"No IP addresses found for hostname: {hostname}")
    
    # 3. Validate protocol and port
    scheme = parsed_url.scheme.lower()
    if scheme not in ['http', 'https']:
        raise ValueError(f"Unsupported scheme: {scheme}")
    
    # Determine default port
    default_port = 80 if scheme == 'http' else 443
    
    # Check if port matches default
    if parsed_url.port:
        if parsed_url.port != default_port:
            raise ValueError(f"Port {parsed_url.port} is not the default port for {scheme}")
    
    # 4. Construct the full URL with the resolved IP
    # We use the first IP address as the base for the path check.
    # Note: The spec says "follow each resolved path", implying we check the path
    # against the root using the resolved IP.
    base_url = f"{scheme}://{ip_addresses[0]}{parsed_url.path}"
    
    # 5. Normalize the path to check for escape attempts
    # We need to ensure the path doesn't escape the root directory.
    # urllib.parse.urljoin is useful, but we must be careful with .. and symlinks.
    # Since we are using the resolved IP, we construct the full URL.
    
    # Normalize the path relative to the base URL
    normalized_path = urllib.parse.urljoin(base_url, '')
    # This effectively cleans up the path.
    normalized_path = normalized_path.rstrip('/')
    
    # Check if the normalized path escapes the root
    # We construct the absolute path for the base URL and compare
    base_path = os.path.join(ROOT_DIR, parsed_url.path)
    # Handle .. in the path
    while '..' in base_path:
        base_path = base_path.replace('..', '')
    
    # A more robust check: resolve the path and see if it starts with the root
    # However, the spec mentions symbolic links. In a pure URL context, we usually
    # check the URL path string itself against the root prefix.
    # Let's use a strict prefix check on the normalized URL path.
    
    # Ensure the path is under the root
    if not base_path.startswith(ROOT_DIR):
        # If the path is absolute, it should be under the root
        raise ValueError(f"Path escapes root: {base_path}")
    
    # Check for .. segments in the path that could escape
    # We can do a simple check by resolving the path components
    path_parts = base_path.split(os.sep)
    # Remove the root part
    relative_parts = path_parts[len(ROOT_DIR.split(os.sep)):] if ROOT_DIR != '.' else path_parts
    
    # Reconstruct and check
    # Actually, a simpler and safer way for URL paths is to check if the path
    # starts with the root directory string.
    if not base_path.startswith(ROOT_DIR):
        raise ValueError(f"Path escapes root: {base_path}")
    
    # 6. Make the request
    try:
        response = transport(url)
    except Exception as e:
        raise ValueError(f"Request failed: {e}")
    
    # 7. Check status code
    status_code = response[0]
    if status_code != 200:
        raise ValueError(f"Status code {status_code} is not 200")
    
    # 8. Return body
    return response[2]
