def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL using the provided transport and host resolver.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The response body if status is 200.
    
    Raises:
        ValueError: If the scheme is not http or https, or if the host cannot be resolved.
    """
    # Check scheme
    if not url.startswith('http://') and not url.startswith('https://'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Extract hostname and port
    if url.startswith('http://'):
        scheme = 'http'
        port = 80
    else:
        scheme = 'https'
        port = 443
    
    # Parse URL to get hostname
    from urllib.parse import urlparse
    parsed = urlparse(url)
    hostname = parsed.hostname
    
    if not hostname:
        raise ValueError("Invalid URL: hostname not found.")
    
    # Resolve hostname
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Host resolution failed: no IP addresses found.")
    
    # Construct the request URL with the resolved IP
    resolved_url = f"{scheme}://{hostname}:{port}/{parsed.path}"
    if parsed.query:
        resolved_url += f"?{parsed.query}"
    
    # Make the request
    status, headers, body = transport(resolved_url)
    
    # Check status code
    if status != 200:
        raise ValueError("Only status 200 is allowed.")
    
    return body
