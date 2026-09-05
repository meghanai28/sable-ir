def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the URL to extract scheme, hostname, and port
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname
    port = parsed.port

    # Validate scheme and port
    allowed_schemes = ['http', 'https']
    allowed_ports = {80: 'http', 443: 'https'}
    
    if scheme not in allowed_schemes:
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    if port is not None and port not in allowed_ports.values():
        raise ValueError(f"Disallowed port: {port}")
    
    # Ensure the scheme matches the port if both are specified
    if port is not None and scheme != allowed_ports[port]:
        raise ValueError(f"Port {port} does not match scheme {scheme}")
    
    # Resolve hostname to IP address(es)
    ip_addresses = resolve_host(hostname)
    
    if not ip_addresses:
        raise ValueError(f"Could not resolve hostname: {hostname}")
    
    # Use the first resolved IP address for the request
    ip_address = ip_addresses[0]
    
    # Construct the full URL with the resolved IP and default port
    if scheme == 'http':
        default_port = 80
    else:
        default_port = 443
    
    # Build the request URL using the resolved IP
    request_url = f"{scheme}://{ip_address}:{default_port}{url[len(parsed.netloc):]}"
    
    # Make the HTTP request
    status, headers, body = transport(request_url)
    
    # Validate status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Return the body as a string
    return body.decode('utf-8') if isinstance(body, bytes) else str(body)
