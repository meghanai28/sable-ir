def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL using the provided transport and hostname resolver.
    
    Args:
        url (str): The URL to fetch (can be absolute or relative, http/https).
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The body of the response if status code is 200.
    
    Raises:
        ValueError: If the scheme is not http/https, if status is not 200, or for disallowed requests.
    """
    # Parse the URL
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    
    # Validate scheme
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only http and https schemes are allowed.")
    
    # Validate port (default ports for http and https)
    port = parsed.port
    if port:
        if scheme == 'http' and port != 80:
            raise ValueError("Only http on port 80 is allowed.")
        if scheme == 'https' and port != 443:
            raise ValueError("Only https on port 443 is allowed.")
    
    # Extract hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname.")
    
    # Resolve hostname
    try:
        resolved_ips = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname: {e}")
    
    if not resolved_ips:
        raise ValueError("No IP addresses resolved for the hostname.")
    
    # Build the URL for transport with resolved IP (to prevent DNS rebinding)
    # We use the first resolved IP
    resolved_url = f"{scheme}://{resolved_ips[0]}{parsed.path}"
    if parsed.query:
        resolved_url += f"?{parsed.query}"
    if parsed.params:
        resolved_url += f"&{parsed.params}"
    
    # Call transport
    status, headers, body = transport(resolved_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
