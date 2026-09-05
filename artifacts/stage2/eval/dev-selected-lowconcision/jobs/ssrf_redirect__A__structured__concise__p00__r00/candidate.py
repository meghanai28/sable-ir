def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict validation and no redirect following.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The body of the response if status is 200.
    
    Raises:
        ValueError: If the scheme is not http or https, or if the hostname cannot be resolved.
    """
    # Guard: Check scheme
    if not url.startswith('http://') and not url.startswith('https://'):
        raise ValueError("Only http and https schemes are allowed")
    
    # Extract scheme and host
    scheme = url.split('://')[0]
    rest = url.split('://')[1]
    
    # Handle port
    if ':' in rest:
        host_port = rest.split(':', 1)
        host = host_port[0]
        port = int(host_port[1])
    else:
        host = rest
        port = 80 if scheme == 'http' else 443
    
    # Guard: Resolve host
    ip_addresses = resolve_host(host)
    if not ip_addresses:
        raise ValueError("Could not resolve hostname")
    
    # Build request URL
    request_url = f"{scheme}://{host}"
    if port != 80 and port != 443:
        request_url += f":{port}"
    if not url.endswith('/'):
        request_url += '/'
    
    # Make request
    status, headers, body = transport(request_url)
    
    # Guard: Check status
    if status != 200:
        raise ValueError("Expected status 200")
    
    # Guard: No redirects allowed, even if they appear public
    # We do not follow any redirects; we only make the initial request.
    # The plan states: "follow only the initial HTTP destination and raise ValueError for every redirect response"
    # Since we are not implementing a redirect loop, we just return the body of the initial request.
    # If the transport function handles redirects internally, we rely on that, but per plan, we do not follow redirects.
    # The plan says "raise ValueError for every redirect response", implying if the response indicates a redirect, we should fail.
    # However, the plan also says "follow only the initial HTTP destination", which suggests we do not make subsequent requests.
    # To be safe and strictly follow the plan: if the response is a redirect (e.g., 301, 302, 303, 307, 308), we raise ValueError.
    # But the plan says "raise ValueError for every redirect response", so we check for redirect status codes.
    
    # Check for redirect status codes
    redirect_codes = [301, 302, 303, 307, 308]
    if status in redirect_codes:
        raise ValueError("Redirects are not allowed")
    
    return body
