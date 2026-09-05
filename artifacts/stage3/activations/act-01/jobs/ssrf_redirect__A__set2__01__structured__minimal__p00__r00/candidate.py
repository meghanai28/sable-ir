def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL using the provided transport function.
    
    Args:
        url: The URL to fetch from.
        transport: A function that takes a URL and returns a tuple (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of textual IP addresses.
    
    Returns:
        The body of the response if the status is 200.
    
    Raises:
        ValueError: If the status is not 200, the port is invalid, or host resolution fails.
    """
    # Parse the URL to extract scheme, netloc, and path
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc
    port = parsed.port
    
    # Determine the default port based on the scheme
    default_port = 80 if scheme == 'http' else 443
    
    # Check if the port is valid for the scheme
    if port is None:
        port = default_port
    elif port != default_port:
        raise ValueError(f"Port {port} is not allowed for {scheme}")
    
    # Extract the hostname from the netloc
    hostname = netloc.split(':')[0]
    
    # Resolve the host's IP address
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError(f"Failed to resolve host {hostname}")
    
    # Construct the full URL with the resolved IP address
    resolved_url = f"{scheme}://{ip_addresses[0]}{url[len(netloc):]}"
    
    # Call the transport function
    status, headers, body = transport(resolved_url)
    
    # Check if the status is 200
    if status == 200:
        return body
    else:
        raise ValueError(f"Status code {status} is not allowed")
