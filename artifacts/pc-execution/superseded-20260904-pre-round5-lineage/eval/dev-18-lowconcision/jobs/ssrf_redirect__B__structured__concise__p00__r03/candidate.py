def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation and redirect handling.
    
    Args:
        url: The target URL string.
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the URL is absolute, has invalid hostname, or fails validation.
    """
    # Guard: Reject absolute URLs
    if url.startswith(("http://", "https://")):
        raise ValueError("Absolute URLs are disallowed")
    
    # Guard: Resolve hostname and validate
    hostname = url.split("://")[1].split("/")[0]
    try:
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError(f"Hostname {hostname} does not resolve to a finite IP address")
    except Exception:
        raise ValueError(f"Invalid hostname: {hostname}")
    
    # Parse initial URL components
    scheme = None
    port = None
    path = url
    if "://" in url:
        parts = url.split("://", 1)
        scheme = parts[0]
        path = parts[1]
    if ":" in path:
        path, port_str = path.split(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid port: {port_str}")
    
    # Determine default port based on scheme
    default_port = 80 if scheme == "http" else 443
    if port is None:
        port = default_port
    
    # Validate scheme
    if scheme not in ("http", "https"):
        raise ValueError(f"Unsupported scheme: {scheme}")
    
    # Build base URL for redirect resolution
    base_url = f"{scheme}://{hostname}:{port}{path}"
    
    current_url = base_url
    max_redirects = 5
    redirect_count = 0
    
    while redirect_count < max_redirects:
        # Check for .. segments in path (basic path traversal guard)
        if ".." in current_url.split("://")[1].split("?")[0].split("/"):
            raise ValueError("Path traversal detected")
        
        # Call transport
        status, headers, body = transport(current_url)
        
        # Check status code
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Extract Location header
        location = None
        for key, value in headers.items():
            if key.lower() == "location":
                location = value
                break
        
        # If no Location header, return body
        if location is None:
            return body
        
        # Guard: Resolve redirect location
        if not location.startswith(("http://", "https://")):
            # Relative path
            current_url = base_url + "/" + location
        else:
            # Absolute URL
            new_scheme, new_port, new_path = parse_location(location)
            
            # Guard: Same scheme and port check
            if new_scheme != scheme or (new_port is not None and new_port != port):
                raise ValueError("Redirect must have same scheme and port")
            
            # Resolve hostname
            new_hostname = new_path.split("://")[1].split("/")[0]
            try:
                new_ip_addresses = resolve_host(new_hostname)
                if not new_ip_addresses:
                    raise ValueError(f"Redirect hostname {new_hostname} does not resolve")
            except Exception:
                raise ValueError(f"Invalid redirect hostname: {new_hostname}")
            
            # Build new URL
            new_base = f"{new_scheme}://{new_hostname}:{new_port}{new_path}"
            current_url = new_base
        
        redirect_count += 1
    
    return body


def parse_location(location: str):
    """
    Parse location string into scheme, port, and path.
    Returns (scheme, port, path) or (scheme, None, path) if no port.
    """
    scheme = None
    path = location
    if "://" in location:
        scheme = location.split("://", 1)[0]
        path = location.split("://", 1)[1]
    if ":" in path:
        path, port_str = path.split(":", 1)
        try:
            port = int(port_str)
            return (scheme, port, path)
        except ValueError:
            return (scheme, None, path)
    return (scheme, None, path)
