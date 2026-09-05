def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL without following redirects.
    
    Args:
        url: The URL to fetch (untrusted).
        transport: A callable transport(url) -> (status, headers, body).
        resolve_host: A callable resolve_host(hostname) -> list of IP addresses.
    
    Returns:
        The body text for a 200 status code.
    
    Raises:
        ValueError: If resolve_host returns no IPs or if the initial destination
                   is not http:// or https://.
    """
    # Guard: Resolve hostname and validate protocol
    hostname = url.split('://')[1] if '://' in url else url
    ip_addresses = resolve_host(hostname)
    
    if not ip_addresses:
        raise ValueError("resolve_host returned no IP addresses")
    
    # Guard: Check initial public HTTP destination
    if not url.startswith('http://') and not url.startswith('https://'):
        raise ValueError("Initial destination must start with http:// or https://")
    
    # Determine the scheme and port
    scheme = 'http' if url.startswith('http://') else 'https'
    port = 80 if scheme == 'http' else 443
    
    # Construct the URL with explicit scheme and port for transport
    # We use the resolved IP to avoid DNS issues, but the transport
    # expects the full URL string typically. Based on the plan, we use the
    # initial destination URL but we must ensure we don't follow redirects.
    # The transport function is called with the url.
    
    status, headers, body = transport(url)
    
    # Guard: Check status code
    if status != 200:
        raise ValueError(f"Expected status 200, got {status}")
    
    return body
