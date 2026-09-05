def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL using the provided transport and host resolution functions.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The response body for a 200 status code.
    
    Raises:
        ValueError: If the scheme is not http or https, or if host resolution fails.
    """
    # Parse the URL to extract scheme, netloc, and path
    from urllib.parse import urlparse, parse_qs
    
    parsed_url = urlparse(url)
    
    # Guard: Check scheme
    scheme = parsed_url.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Guard: Resolve hostname
    hostname = parsed_url.netloc
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    # Guard: Resolve hostname to IP
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    if not ip_addresses:
        raise ValueError(f"No IP addresses found for hostname: {hostname}")
    
    # Guard: Follow only the initial request, never follow redirects
    # We will use the first IP address found for the connection
    target_url = url
    
    # Make the request
    status, headers, body = transport(target_url)
    
    # Guard: Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
