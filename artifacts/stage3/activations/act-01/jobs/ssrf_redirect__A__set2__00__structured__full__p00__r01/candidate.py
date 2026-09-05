def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL using the provided transport and host resolver.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns a tuple (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The response body if status is 200.
    
    Raises:
        ValueError: If the scheme is not http or https, or if host resolution fails.
    """
    from urllib.parse import urlparse
    
    # Parse the URL
    parsed_url = urlparse(url)
    
    # Guard: Check scheme
    scheme = parsed_url.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Determine the host
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname.")
    
    # Guard: Resolve host
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Failed to resolve hostname.")
    
    if not ip_addresses:
        raise ValueError("No IP addresses found for hostname.")
    
    # Determine the port
    port = parsed_url.port
    if port is None:
        if scheme == 'http':
            port = 80
        else:
            port = 443
    else:
        # Guard: Check if the port is the default port for the scheme
        if (scheme == 'http' and port != 80) or (scheme == 'https' and port != 443):
            raise ValueError("Only default ports are allowed for HTTP and HTTPS.")
    
    # Construct the request URL with the resolved IP
    # Note: We use the first IP address as per the plan's implication of "the first validated request"
    request_url = parsed_url._replace(netloc=f"[{ip_addresses[0]}]:{port}", path=parsed_url.path, params=parsed_url.params, query=parsed_url.query).geturl()
    
    # Make the request
    status, headers, body = transport(request_url)
    
    # Guard: Check status code
    if status != 200:
        raise ValueError("Only status code 200 is allowed.")
    
    # Return the body
    return body
