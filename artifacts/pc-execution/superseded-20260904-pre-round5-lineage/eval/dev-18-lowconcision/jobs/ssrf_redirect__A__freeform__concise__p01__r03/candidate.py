def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL using the provided transport and hostname resolver.
    
    Args:
        url (str): The URL to fetch (can be absolute or relative).
        transport (callable): A function that takes a URL and returns a (status, headers, body) tuple.
        resolve_host (callable): A function that takes a hostname and returns a list of textual IP addresses.
    
    Returns:
        str: The body of the response for status 200.
    
    Raises:
        ValueError: If the request is disallowed (e.g., absolute URL, no IP address, or non-HTTP scheme).
    """
    # Parse the URL
    from urllib.parse import urlparse, urljoin
    
    parsed_url = urlparse(url)
    
    # Check for absolute URLs
    if parsed_url.scheme and parsed_url.netloc:
        raise ValueError("Absolute URLs are not allowed.")
    
    # Default to HTTP if no scheme is provided
    if not parsed_url.scheme:
        parsed_url = parsed_url._replace(scheme='http')
    
    # Check scheme
    if parsed_url.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Resolve hostname
    hostname = parsed_url.netloc if parsed_url.netloc else parsed_url.path.split('/')[0]
    
    # Check if hostname is valid (has an IP address)
    if not hostname or not resolve_host(hostname):
        raise ValueError("Hostname must have an IP address.")
    
    # Construct the full URL for transport
    if parsed_url.scheme == 'http':
        default_port = 80
    else:
        default_port = 443
    
    full_url = f"{parsed_url.scheme}://{hostname}"
    
    # Make the request
    status, headers, body = transport(full_url)
    
    # Check status code
    if status != 200:
        raise ValueError("Only status 200 is allowed.")
    
    return body
