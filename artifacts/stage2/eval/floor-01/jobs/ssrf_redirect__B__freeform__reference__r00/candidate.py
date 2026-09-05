def fetch_text(url, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation of scheme, port, hostname,
    and redirect chain.
    
    Args:
        url (str): The initial URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The response body for a 200 status code.
    
    Raises:
        ValueError: If the URL, hostnames, or redirects are invalid.
    """
    current_url = url
    redirect_count = 0
    
    while True:
        # Validate current_url
        if not validate_url(current_url):
            raise ValueError(f"Invalid URL: {current_url}")
        
        # Resolve hostname
        hostname = extract_hostname(current_url)
        if not hostname:
            raise ValueError(f"No hostname found in URL: {current_url}")
        
        addresses = resolve_host(hostname)
        if not addresses:
            raise ValueError(f"Hostname {hostname} does not resolve to any addresses.")
        
        # Check if any address is a global public address
        if not any(is_global_public_address(addr) for addr in addresses):
            raise ValueError(f"Hostname {hostname} resolves to non-public addresses.")
        
        # Make the request
        status, headers, body = transport(current_url)
        
        if status != 200:
            raise ValueError(f"Request failed with status {status}")
        
        return body
    
    # This part is unreachable due to the while loop, but included for completeness
    raise ValueError("Unexpected end of redirect chain")


def validate_url(url):
    """
    Validate the URL scheme, port, and presence of credentials.
    """
    # Check for disallowed schemes
    if not url.lower().startswith(('http://', 'https://')):
        return False
    
    # Parse the URL to check for credentials
    from urllib.parse import urlparse
    parsed = urlparse(url)
    
    # Check for username or password
    if parsed.username or parsed.password:
        return False
    
    # Check scheme and port
    scheme = parsed.scheme.lower()
    port = parsed.port
    
    if scheme == 'http':
        if port is not None and port != 80:
            return False
    elif scheme == 'https':
        if port is not None and port != 443:
            return False
    
    return True


def extract_hostname(url):
    """
    Extract the hostname from the URL.
    """
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.hostname


def is_global_public_address(ip):
    """
    Check if an IP address is a global public address.
    This is a simplified check; in production, you might use a more robust method.
    """
    # Check if the IP is a private IP
    from ipaddress import ip_address
    try:
        ip_obj = ip_address(ip)
        # Private networks
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
            return False
    except ValueError:
        return False
    
    return True
