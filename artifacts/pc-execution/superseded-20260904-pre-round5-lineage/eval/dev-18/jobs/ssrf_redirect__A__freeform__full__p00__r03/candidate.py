def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL using the provided transport and host resolver.
    
    Args:
        url (str): The URL to fetch (supports http/https with query/fragment).
        transport (callable): Function(url) -> (status, headers, body) tuple.
        resolve_host (callable): Function(hostname) -> list of textual IP addresses.
    
    Returns:
        str: The response body for status 200.
    
    Raises:
        ValueError: If the scheme/port is disallowed or status is not 200.
    """
    import socket
    import urllib.parse
    
    # Parse URL components
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    path = parsed.path
    port = parsed.port
    host = parsed.hostname
    
    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    # Determine default port
    default_port = 80 if scheme == 'http' else 443
    
    # Adjust port if specified
    if port is None:
        port = default_port
    else:
        if port != default_port:
            raise ValueError(f"Non-default port {port} not allowed for scheme {scheme}")
    
    # Resolve hostname
    if not host:
        raise ValueError("Invalid URL: missing hostname")
    
    ip_addresses = resolve_host(host)
    if not ip_addresses:
        raise ValueError(f"Could not resolve hostname: {host}")
    
    # Use the first resolved IP
    resolved_ip = ip_addresses[0]
    
    # Construct the request URL for transport (without query/fragment for body extraction)
    # The transport function is expected to handle the full URL or we pass the path.
    # Based on the plan: "transport(url) returns..." and we need to capture status 200.
    # We assume transport expects the full URL string.
    request_url = f"{scheme}://{resolved_ip}:{port}{path}"
    
    # Call transport
    status, headers, body = transport(request_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
