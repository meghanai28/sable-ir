def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict security constraints.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): Function(url) -> (status, headers, body) tuple.
        resolve_host (callable): Function(hostname) -> list of IP address strings.
    
    Returns:
        str: The response body for status 200.
    
    Raises:
        ValueError: If the scheme is not http/https, or if redirect attempts are made.
    """
    import socket
    import urllib.parse
    
    # Parse the URL to get scheme and host
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname
    
    # Guard: Check scheme
    if scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    # Guard: Resolve host
    try:
        ip_addresses = resolve_host(host)
        if not ip_addresses:
            raise ValueError(f"Failed to resolve host: {host}")
    except Exception as e:
        raise ValueError(f"Host resolution failed: {e}")
    
    # Determine port based on scheme
    if scheme == 'http':
        port = 80
    else:  # https
        port = 443
    
    # Make the request
    status, headers, body = transport(url)
    
    # Guard: Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
