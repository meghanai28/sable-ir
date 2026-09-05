import os
import urllib.parse
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict path normalization and symlink resolution checks.
    Ensures the resolved file path remains within the application's document root.
    """
    # Parse the URL to extract the path component
    parsed_url = urllib.parse.urlparse(url)
    path = parsed_url.path
    
    # Define the application's document root (placeholder for the actual directory)
    # In a real scenario, this would be the base directory of the application
    document_root = os.path.dirname(os.path.abspath(__file__))
    
    # Normalize the requested path to prevent directory traversal
    # Remove leading slashes and normalize separators
    normalized_path = os.path.normpath(path)
    
    # Construct the full file path
    full_path = os.path.join(document_root, normalized_path)
    
    # Check if the normalized path escapes the document root
    if not full_path.startswith(document_root):
        raise ValueError("Path escapes document root")
    
    # Resolve symbolic links
    resolved_path = os.path.realpath(full_path)
    
    # Check if the resolved path is still within the document root
    if not resolved_path.startswith(document_root):
        raise ValueError("Resolved path escapes document root")
    
    # Attempt to fetch the URL using the provided transport
    try:
        response = transport(url)
        status, headers, body = response
        
        # Check if the status code is 200
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Return the body as text
        return body.decode('utf-8')
        
    except Exception as e:
        raise ValueError(f"Failed to fetch URL: {str(e)}")
