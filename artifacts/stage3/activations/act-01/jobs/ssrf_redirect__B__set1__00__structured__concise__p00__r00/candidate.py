def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL using the provided transport and host resolution functions.
    
    Args:
        url: The URL to fetch from.
        transport: A function that takes a URL and returns a (status, headers, body) tuple.
        resolve_host: A function that takes a hostname and returns textual IP addresses.
    
    Returns:
        The body of the HTTP response as a string if status is 200.
    
    Raises:
        ValueError: If the scheme is not HTTP or HTTPS, or if the resolved IP does not match the scheme's address family.
    """
    # Parse the URL to extract scheme and host
    from urllib.parse import urlparse
    parsed = urlparse(url)
    
    scheme = parsed.scheme.lower()
    host = parsed.hostname
    port = parsed.port
    
    # Guard: Check scheme
    if scheme not in ['http', 'https']:
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Guard: Resolve host and check IP address
    if not host:
        raise ValueError("Invalid URL: missing host.")
    
    ip_addresses = resolve_host(host)
    if not ip_addresses:
        raise ValueError("resolve_host returned no IP addresses.")
    
    # Determine the expected address family based on the scheme
    if scheme == 'http':
        expected_family = 'IPv4'  # HTTP default is 80, which is IPv4
    else:  # https
        expected_family = 'IPv4'  # HTTPS default is 443, which is IPv4
    
    # Guard: Check if the resolved IP belongs to the requested scheme's address family
    # Note: In practice, both HTTP and HTTPS can use IPv6, but the plan specifies checking against the scheme's default.
    # We will check if at least one resolved IP matches the expected family.
    valid_ip = False
    for ip in ip_addresses:
        # Simple check: if the IP contains a colon, it's IPv6; otherwise, it's IPv4
        if ':' in ip:
            if expected_family == 'IPv4':
                # If scheme expects IPv4 but we got IPv6, it's invalid for this implementation's guard
                continue
            else:
                valid_ip = True
        else:
            valid_ip = True
    
    if not valid_ip:
        raise ValueError("Resolved IP does not belong to the requested scheme's address family.")
    
    # Determine the port
    default_port = 80 if scheme == 'http' else 443
    if port is None:
        port = default_port
    else:
        port = int(port)
    
    # Construct the URL for the transport function
    # We use the resolved IP if available, otherwise fall back to the host
    if host:
        constructed_url = f"{scheme}://{host}"
        if port != default_port:
            constructed_url += f":{port}"
    else:
        constructed_url = f"{scheme}://{host}"
    
    # Create the request using the transport function
    status, headers, body = transport(constructed_url)
    
    # Return the body only for status 200
    if status == 200:
        return body
    else:
        raise ValueError(f"Unexpected status code: {status}")
