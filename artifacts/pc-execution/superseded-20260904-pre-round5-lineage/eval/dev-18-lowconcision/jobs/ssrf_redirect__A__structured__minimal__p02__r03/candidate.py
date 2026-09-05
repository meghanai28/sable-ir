def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation.
    
    Args:
        url: The URL to fetch.
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of textual IP addresses.
    
    Returns:
        The body of the response for status 200.
    
    Raises:
        ValueError: If the scheme is not HTTP/HTTPS on default port,
                    if the hostname does not resolve, or if a redirect is followed.
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    
    # GUARD: Check scheme and port
    scheme = parsed.scheme.lower()
    port = parsed.port
    
    # Default ports: HTTP=80, HTTPS=443
    if scheme == 'http':
        allowed_port = 80
    elif scheme == 'https':
        allowed_port = 443
    else:
        raise ValueError("Disallowed scheme")
    
    # Check if port is default (None or the specific number)
    if port is not None and port != allowed_port:
        raise ValueError("Non-default port")
    
    # ORDER: Resolve hostname before making request
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid URL hostname")
    
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError("Hostname resolution failed")
    
    if not resolved_ips:
        raise ValueError("Hostname did not resolve")
    
    # ORDER: Capture initial destination
    initial_destination = parsed.netloc + parsed.path + parsed.params + parsed.query
    if parsed.fragment:
        initial_destination += "#" + parsed.fragment
    
    # Make the network request
    status, headers, body = transport(url)
    
    # GUARD: Reject every redirect response
    if status == 300 or status == 301 or status == 302 or status == 303 or status == 307 or status == 308:
        raise ValueError("Redirect not allowed")
    
    # EFFECT: Return body for status 200
    if status == 200:
        return body
    else:
        raise ValueError("Unexpected status code")
