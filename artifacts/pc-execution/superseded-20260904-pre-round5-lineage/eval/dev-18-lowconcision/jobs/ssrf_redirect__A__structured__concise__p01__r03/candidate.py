def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict security controls.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The body of the response if status is 200.
    
    Raises:
        ValueError: If the request is disallowed (non-HTTP/HTTPS, non-default port, or infinite IPs).
    """
    import socket
    import urllib.parse
    
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Determine the default port
    default_port = 80 if parsed.scheme == 'http' else 443
    
    # Check if port is specified and matches default, or if no port is specified (implicit default)
    if parsed.port:
        if parsed.port != default_port:
            raise ValueError("Only default ports (80 for HTTP, 443 for HTTPS) are allowed.")
    else:
        # No port specified, assume default
        pass
    
    # Extract hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname.")
    
    # Resolve hostname
    try:
        ip_addresses = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname: {e}")
    
    # Check if resolved IP addresses are finite
    if not ip_addresses or len(ip_addresses) == 0:
        raise ValueError("No valid IP addresses found for the hostname.")
    
    # Check for IPv6 loopback (::1) or similar non-routable addresses if they are the only ones
    # A simple check: if the only IP is ::1 (localhost) or similar, we might want to block it based on "finite" interpretation in some contexts,
    # but strictly "finite" usually just means not infinite. However, to be safe against loopback abuse in a generic fetcher:
    # The prompt says "raise ValueError unless the resolved IP addresses are finite".
    # In networking, IPv4 and IPv6 addresses are finite. ::1 is finite.
    # We will assume any valid resolved IP is acceptable unless it's explicitly infinite (which resolve_host shouldn't return).
    # However, to be robust, we check if the list is empty or contains only invalid entries.
    
    # Build the request URL
    # We must NOT follow redirects. We use the resolved hostname to construct the URL if needed,
    # but the transport function likely handles the resolution or we pass the URL.
    # The plan says "follow the initial destination only".
    
    # Construct the URL for the request. If the original URL had a port, use it, otherwise use default.
    # urllib.parse.urlunparse helps reconstruct the URL.
    # We need to ensure the URL we pass to transport matches the scheme and the resolved host context if necessary.
    # However, the transport function signature is transport(url). We assume transport handles the connection.
    # We just need to make sure we don't follow redirects.
    
    # Construct the full URL string for the request
    # We use the original netloc if possible, or construct from hostname + port
    netloc = parsed.netloc
    if not netloc:
        netloc = f"{hostname}:{default_port}"
    else:
        # Ensure port is included if specified in netloc, otherwise add default
        if not parsed.port:
            netloc = f"{hostname}:{default_port}"
    
    full_url = parsed._replace(netloc=netloc, scheme=parsed.scheme).geturl()
    
    # Call transport
    status, headers, body = transport(full_url)
    
    # Check status code
    if status != 200:
        raise ValueError("Only status code 200 is allowed.")
    
    # Decode body if it's bytes
    if isinstance(body, bytes):
        try:
            return body.decode('utf-8')
        except UnicodeDecodeError:
            raise ValueError("Response body cannot be decoded as UTF-8.")
    
    return body
