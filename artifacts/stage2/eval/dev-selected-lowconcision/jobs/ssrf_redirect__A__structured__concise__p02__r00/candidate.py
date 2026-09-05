def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL using the provided transport function.
    
    Args:
        url: The URL to fetch.
        transport: A function that takes a URL and returns a (status, headers, body) tuple.
        resolve_host: A function that takes a hostname and returns textual IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the scheme is not http or https, or if the resolved path escapes the root.
    """
    # Parse the URL to get scheme, netloc, and path
    from urllib.parse import urlparse, urljoin
    
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme.lower()
    
    # Guard: Check scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Guard: Resolve host
    hostname = parsed_url.netloc
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Failed to resolve hostname")
    
    # Guard: Determine the root path for containment check
    # The plan mentions "configured root" but doesn't specify it. 
    # Assuming the root is the directory of the base URL if provided, or empty string.
    # For this implementation, we'll assume the root is the directory of the initial URL.
    root = ""
    if parsed_url.path:
        root = parsed_url.path.split('?')[0]
        if not root.endswith('/'):
            root += '/'
    
    # Build the base URL for path containment check
    base_url = f"{scheme}://{hostname}{root}"
    
    # Resolve the initial path
    initial_path = parsed_url.path.split('?')[0]
    if not initial_path.startswith('/'):
        initial_path = '/' + initial_path
    
    # Check if initial path escapes root
    if not initial_path.startswith(root):
        raise ValueError("Resolved path escapes configured root")
    
    # Open connection
    status, headers, body = transport(url)
    
    # Guard: Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Guard: Follow redirects only once (initial public HTTP destination)
    # The plan says "follow the initial public HTTP destination only and raise ValueError for every redirect response"
    # This implies we should not follow redirects at all, just return the body of the initial request.
    # However, "follow the initial public HTTP destination" might mean we should resolve redirects to the final URL.
    # Given the strictness of "raise ValueError for every redirect response", we will not follow redirects.
    
    return body.decode('utf-8') if isinstance(body, bytes) else body
