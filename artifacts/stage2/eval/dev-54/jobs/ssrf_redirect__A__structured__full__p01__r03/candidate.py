def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL, resolving hostnames and validating the scheme.
    
    Args:
        url: The URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the scheme is not http or https, or if host resolution fails.
    """
    # Parse the URL to extract scheme and host
    from urllib.parse import urlparse, parse_qs
    
    parsed = urlparse(url)
    
    # Check scheme
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Resolve host
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid URL: hostname not found.")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Host resolution failed.")
    
    # Use the first IP address for the request
    ip_address = ip_addresses[0]
    
    # Build the request URL
    request_url = f"{scheme}://{ip_address}{parsed.path}"
    if parsed.params:
        request_url += f"?{parsed.params}"
    if parsed.query:
        request_url += f"&{parsed.query}"
    
    # Make the request
    status, headers, body = transport(request_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Decode body to string if it's bytes
    if isinstance(body, bytes):
        body = body.decode('utf-8')
    
    return body
