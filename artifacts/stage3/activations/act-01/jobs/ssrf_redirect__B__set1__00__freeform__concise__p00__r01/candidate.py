def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL using the provided transport and host resolver.
    
    Args:
        url: The URL to fetch from (untrusted input).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns textual IP addresses.
    
    Returns:
        The body text for a successful HTTP 200 response.
    
    Raises:
        ValueError: If the scheme is not http/https, host cannot be resolved,
                   resolved IP does not match requested host, or status is not 200.
    """
    # Parse URL components
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    
    # Validate scheme
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Extract host and port
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing host.")
    
    # Default port handling
    default_port = {
        'http': 80,
        'https': 443
    }
    
    port = parsed.port
    if port is None:
        port = default_port[scheme]
    
    # Construct the full URL for transport
    full_url = parsed._replace(port=port).geturl()
    
    # Resolve host
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError("Host cannot be resolved.")
    
    if not resolved_ips:
        raise ValueError("Host resolution returned no IP addresses.")
    
    # Validate that resolved IP belongs to the requested host
    # This check ensures we are not following DNS redirects to different hosts
    for ip in resolved_ips:
        if ip != hostname:
            raise ValueError("Resolved IP does not match requested host (potential DNS redirect).")
    
    # Perform the transport
    status, headers, body = transport(full_url)
    
    # Check status code
    if status != 200:
        raise ValueError("Only HTTP 200 status code is allowed.")
    
    # Return body text
    return body
