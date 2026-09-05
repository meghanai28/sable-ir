def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetches text from a URL using the provided transport and host resolver.
    
    Args:
        url: The URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the scheme is not http or https, or if resolve_host returns no IPs.
    """
    # Resolve the hostname
    hostname = url.split('://')[1].split('/')[0]
    ip_addresses = resolve_host(hostname)
    
    if not ip_addresses:
        raise ValueError("resolve_host returned no IP addresses")
    
    # Check the scheme
    scheme = url.split('://')[0]
    if scheme.lower() not in ['http', 'https']:
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Open the connection using the transport
    status, headers, body = transport(url)
    
    # Check the status code
    if status != 200:
        raise ValueError(f"Expected status 200, got {status}")
    
    return body
