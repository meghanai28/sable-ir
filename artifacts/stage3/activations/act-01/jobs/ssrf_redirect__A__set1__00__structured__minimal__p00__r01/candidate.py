def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL, validating scheme and hostname resolution.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The body of the response for status 200.
    
    Raises:
        ValueError: If the scheme is not http or https, or if hostname resolution fails.
    """
    # Validate scheme
    scheme = url.split("://")[0]
    if scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Resolve hostname
    hostname = url.split("://")[1].split("?")[0]
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Failed to resolve hostname")
    
    if not ip_addresses:
        raise ValueError("Hostname resolution returned no IP addresses")
    
    # Determine the default port based on scheme
    default_port = 80 if scheme == "http" else 443
    
    # Extract the full URL without query string for transport
    base_url = url.split("?")[0]
    
    # Call transport
    status, headers, body = transport(base_url)
    
    # Check status code
    if status != 200:
        raise ValueError("Only status 200 is allowed")
    
    return body
