def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security constraints.
    
    Args:
        url: The URL to fetch.
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of textual IP addresses.
    
    Returns:
        The text body for a 200 status code.
    
    Raises:
        ValueError: If the URL scheme/port is invalid, hostname resolution fails,
                    or the final destination differs from the initial request.
    """
    # Parse the URL to check scheme and port
    from urllib.parse import urlparse
    
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme.lower()
    port = parsed_url.port
    
    # Validate scheme: only HTTP or HTTPS on default port
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP or HTTPS schemes are allowed")
    
    default_port = {'http': 80, 'https': 443}[scheme]
    
    if port is None:
        port = default_port
    elif port != default_port:
        raise ValueError("Only default ports are allowed")
    
    hostname = parsed_url.hostname
    if hostname is None:
        raise ValueError("Invalid URL")
    
    # Resolve hostname before opening connection
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError("Hostname resolution failed")
    
    if not resolved_ips:
        raise ValueError("No IP addresses resolved for hostname")
    
    # Make the transport request
    status, headers, body = transport(url)
    
    # Check status code
    if status != 200:
        raise ValueError("Only status 200 is allowed")
    
    # Check final destination before reading body
    final_url = headers.get('location')
    final_scheme = final_url.split('://')[0].lower() if final_url else scheme
    final_path = final_url.split('://')[1].split('?')[0] if final_url else parsed_url.path
    
    # Reconstruct the final URL to check scheme and port
    # If no port specified in redirect, assume default for the scheme
    final_port = None
    if ':' in final_path:
        # Handle port in path (e.g., http://host:8080/path)
        final_port_str = final_path.split(':')[0].split('/')[0]
        if final_port_str.isdigit():
            final_port = int(final_port_str)
            final_path = final_path.split(':')[1]
    
    if final_scheme != scheme:
        raise ValueError("Final destination scheme must match initial scheme")
    
    if final_port is not None and final_port != default_port:
        raise ValueError("Final destination port must match initial port")
    
    # Read and return the body
    return body.decode('utf-8') if isinstance(body, bytes) else body
