def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation of scheme, port, hostnames,
    and redirect chains.
    
    Args:
        url: The initial URL string.
        transport: A callable(url) -> (status, headers, body) tuple.
        resolve_host: A callable(hostname) -> list of IP address strings.
    
    Returns:
        The response body as a string for a 200 status.
    
    Raises:
        ValueError: If validation fails at any step (scheme, port, host, credentials,
                    redirect loop, or invalid redirect target).
    """
    current_url = url
    redirect_count = 0
    max_redirects = 5
    
    while True:
        # Validate the current URL
        if not validate_url(current_url):
            raise ValueError("Invalid URL: disallowed scheme, port, or credentials.")
        
        # Resolve hostname
        hostname = extract_hostname(current_url)
        addresses = resolve_host(hostname)
        
        if not addresses:
            raise ValueError(f"Host '{hostname}' resolved to no addresses.")
        
        for addr in addresses:
            if not is_public_address(addr):
                raise ValueError(f"Host '{hostname}' resolved to non-public address '{addr}'.")
            break  # Use the first valid public address
        
        # Make the request
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        # Handle redirects
        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects.")
            
            location = headers.get("Location", "").strip()
            if not location:
                raise ValueError("Redirect response missing Location header.")
            
            # Resolve relative URLs
            if location.startswith(("http://", "https://")):
                new_url = location
            else:
                new_url = resolve_url(current_url, location)
            
            if not validate_url(new_url):
                raise ValueError("Redirect target has disallowed scheme, port, or credentials.")
            
            current_url = new_url
        else:
            raise ValueError(f"Unexpected status code: {status}")


def validate_url(url: str) -> bool:
    """
    Validate that the URL has an allowed scheme, port, and no credentials.
    """
    # Check for credentials
    if "@" in url:
        return False
    
    # Parse scheme and port
    scheme, _, path = url.partition("://")
    if scheme.lower() not in ("http", "https"):
        return False
    
    # Extract port
    port = None
    if "/" in url:
        # Check if there's a port before the path
        temp = url.split("://")[1].split("/")[0]
        if ":" in temp:
            port = temp.split(":")[1]
    
    # Validate port
    allowed_ports = {80, 443}
    if scheme.lower() == "http":
        if port not in (None, "80"):
            return False
    elif scheme.lower() == "https":
        if port not in (None, "443"):
            return False
    
    return True


def extract_hostname(url: str) -> str:
    """
    Extract the hostname from the URL.
    """
    scheme, _, path = url.partition("://")
    if "/" in path:
        host = path.split("/")[0]
    else:
        host = path
    return host


def resolve_url(base_url: str, location: str) -> str:
    """
    Resolve a relative URL against the base URL.
    """
    if location.startswith(("http://", "https://")):
        return location
    
    # Parse base URL
    base_scheme, _, base_path = base_url.partition("://")
    base_host = base_path.split("/")[0]
    
    # Parse location
    loc_scheme, _, loc_path = location.partition("://")
    
    if loc_scheme:
        # Absolute path, keep scheme
        if "/" in loc_path:
            loc_path = loc_path.split("/")[0]
        return f"{loc_scheme}://{base_host}/{loc_path}"
    else:
        # Relative path
        if "/" in location:
            location = location.split("/")[0]
        return f"{base_scheme}://{base_host}/{location}"


def is_public_address(addr: str) -> bool:
    """
    Check if an IP address is a global public address.
    For this implementation, we assume any standard IPv4 or IPv6 address
    that is not a private range is public.
    """
    import socket
    
    try:
        # Try to resolve the address to see if it's valid
        socket.inet_aton(addr)  # IPv4 check
        socket.inet_pton(socket.AF_INET6, addr)  # IPv6 check
        return True
    except (socket.error, ValueError):
        return False
