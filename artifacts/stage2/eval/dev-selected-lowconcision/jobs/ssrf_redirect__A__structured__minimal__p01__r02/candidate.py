def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict validation and safety checks.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The body of the response for status 200.
    
    Raises:
        ValueError: If the URL is invalid, port is not 80 or 443, path traversal is detected, or status is not 200.
    """
    import urllib.parse
    
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme
    if parsed.scheme.lower() not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Validate port
    port = parsed.port
    if port is None:
        if parsed.scheme.lower() == 'http':
            port = 80
        else:
            port = 443
    
    if port not in (80, 443):
        raise ValueError("Only ports 80 and 443 are allowed")
    
    # Resolve hostname to IP
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid hostname in URL")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Failed to resolve hostname")
    
    if not ip_addresses:
        raise ValueError("No IP addresses found for hostname")
    
    # Check for path traversal
    # Normalize the path to remove .. segments and check for absolute paths
    path = parsed.path
    if path:
        # Ensure path starts with /
        if not path.startswith('/'):
            path = '/' + path
        
        # Normalize the path
        normalized_path = urllib.parse.unquote(path)
        # Remove leading slashes and split
        parts = normalized_path.lstrip('/').split('/')
        
        # Check for ..
        if '..' in parts:
            raise ValueError("Path traversal detected")
    
    # Check for absolute path (starting with /)
    if path.startswith('/'):
        # This is allowed as long as it's not a root traversal attempt
        pass
    
    # Make the request
    status, headers, body = transport(url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Return body
    if body is None:
        raise ValueError("Response body is None")
    
    if isinstance(body, bytes):
        return body.decode('utf-8')
    return body
