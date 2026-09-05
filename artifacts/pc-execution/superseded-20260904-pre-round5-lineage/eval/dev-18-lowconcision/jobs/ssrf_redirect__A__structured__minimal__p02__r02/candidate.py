def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security checks.
    
    Args:
        url: The URL to fetch (untrusted input).
        transport: A callable transport(url) -> (status, headers, body).
        resolve_host: A callable resolve_host(hostname) -> list of textual IP addresses.
    
    Returns:
        The body of the HTTP response if status is 200.
    
    Raises:
        ValueError: If scheme is not HTTP/HTTPS on default port, 
                   if hostname does not resolve, or if redirect is followed.
    """
    # Parse the URL to extract scheme, netloc, and path
    from urllib.parse import urlparse, urljoin
    
    parsed = urlparse(url)
    
    # GUARD: Check scheme and port
    allowed_schemes = {'http', 'https'}
    if parsed.scheme not in allowed_schemes:
        raise ValueError(f"Disallowed scheme: {parsed.scheme}")
    
    default_port = {'http': 80, 'https': 443}
    actual_port = parsed.port
    
    if actual_port is None:
        actual_port = default_port.get(parsed.scheme)
    
    if actual_port is None:
        raise ValueError(f"Unknown scheme port: {parsed.scheme}")
    
    if actual_port != default_port.get(parsed.scheme):
        raise ValueError(f"Non-default port for {parsed.scheme}: {actual_port}")
    
    # ORDER: Resolve the initial hostname before any network request
    hostname = parsed.netloc
    if not hostname:
        raise ValueError("Missing hostname in URL")
    
    # Handle IPv6 addresses in netloc (e.g., [::1])
    if hostname.startswith('['):
        # Extract the IP from IPv6 bracket notation
        end_bracket = hostname.find(']')
        if end_bracket != -1:
            hostname = hostname[1:end_bracket]
    
    # Resolve hostname
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    if not resolved_ips:
        raise ValueError(f"Hostname does not resolve: {hostname}")
    
    # Build the initial request URL (without query string for simplicity, or keep if desired)
    # We will use the netloc and path from the parsed URL
    initial_url = f"{parsed.scheme}://{hostname}{parsed.path}"
    
    # Capture the initial destination
    initial_destination = initial_url
    
    # Make the network request
    status, headers, body = transport(initial_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # GUARD: Reject every redirect response, even one that appears public
    # We do not follow redirects as per the plan.
    # If the response indicates a redirect, we raise an error.
    # Note: The plan says "reject every redirect response", implying we stop there.
    # We assume the transport might return a 3xx status or we check for Location header.
    # However, the plan says "follow the initial public destination but reject every redirect response".
    # This implies we do NOT follow redirects. We just return the body of the initial request.
    # If the initial request was a redirect (3xx), we should raise ValueError.
    
    # Check for redirect status codes (typically 3xx)
    if 300 <= status < 400:
        raise ValueError("Redirect response detected and rejected as per security policy")
    
    # Return the body
    return body
