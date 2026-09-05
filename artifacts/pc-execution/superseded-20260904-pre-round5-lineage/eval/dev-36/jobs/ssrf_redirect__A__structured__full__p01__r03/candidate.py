def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation.
    
    Args:
        url: The URL to fetch (untrusted input).
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of textual IP addresses.
    
    Returns:
        The body text of the response for status 200.
    
    Raises:
        ValueError: If the request is disallowed (wrong scheme, non-default port, 
                   failed resolution, or follows a redirect).
    """
    import urllib.parse
    import socket
    
    # Parse the initial URL to check scheme and port
    parsed_url = urllib.parse.urlparse(url)
    initial_scheme = parsed_url.scheme.lower()
    initial_port = parsed_url.port
    if initial_port is None:
        if initial_scheme == 'http':
            initial_port = 80
        elif initial_scheme == 'https':
            initial_port = 443
        else:
            raise ValueError("Unsupported scheme")
    
    # Resolve the hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError("Failed to resolve hostname")
    
    if not resolved_ips:
        raise ValueError("Resolution failed or returned no addresses")
    
    # Define the allowed scheme and port for the final destination
    allowed_scheme = None
    allowed_port = None
    
    if initial_scheme == 'http':
        allowed_scheme = 'http'
        allowed_port = 80
    elif initial_scheme == 'https':
        allowed_scheme = 'https'
        allowed_port = 443
    else:
        raise ValueError("Unsupported scheme")
    
    # Fetch the response
    status, headers, body = transport(url)
    
    # Check for redirect
    if status == 301 or status == 302:
        raise ValueError("Redirects are not allowed")
    
    # Check status code
    if status != 200:
        raise ValueError("Unexpected status code")
    
    # Parse the final destination from headers (Location header)
    final_url = None
    if 'location' in headers.lower():
        location_value = headers['location'].lower()
        # Handle relative URLs
        if not location_value.startswith(('http://', 'https://')):
            parsed_url = urllib.parse.urlparse(url)
            final_url = urllib.parse.urljoin(parsed_url.geturl(), location_value)
        else:
            final_url = location_value
    else:
        final_url = url
    
    # Parse the final URL to check scheme and port
    final_parsed = urllib.parse.urlparse(final_url)
    final_scheme = final_parsed.scheme.lower()
    final_port = final_parsed.port
    if final_port is None:
        if final_scheme == 'http':
            final_port = 80
        elif final_scheme == 'https':
            final_port = 443
        else:
            raise ValueError("Unsupported scheme in final URL")
    
    # Validate final destination
    if final_scheme != allowed_scheme or final_port != allowed_port:
        raise ValueError("Final destination must be on the same scheme and default port as the requested URL")
    
    # Return the body text
    if isinstance(body, bytes):
        return body.decode('utf-8')
    return str(body)
