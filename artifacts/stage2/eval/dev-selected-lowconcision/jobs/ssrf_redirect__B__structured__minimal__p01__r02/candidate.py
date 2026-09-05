def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL using the provided transport and hostname resolver.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The body of the response for status 200.
    
    Raises:
        ValueError: If the scheme is not http or https, or if resolve_host returns no IP.
    """
    # Check scheme
    scheme = url.split("://")[0]
    if scheme not in ("http", "https"):
        raise ValueError("Only http and https schemes are allowed")
    
    # Parse URL components
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        port = parsed.port
        path = parsed.path
    except Exception:
        raise ValueError("Invalid URL format")
    
    # Resolve hostname
    if not hostname:
        raise ValueError("No hostname in URL")
    
    ips = resolve_host(hostname)
    if not ips:
        raise ValueError("No IP addresses found for hostname")
    
    # Use first IP address for connection
    ip_address = ips[0]
    
    # Construct effective URL with resolved IP if needed (though transport likely handles this)
    # For this implementation, we assume transport can handle the hostname, but we use the IP if required
    # Since the spec says transport(url) returns status, headers, body, we pass the original URL
    # However, to ensure we use the resolved IP, we might need to modify the URL if the transport doesn't handle DNS resolution internally.
    # Given the spec, we assume transport handles the URL as provided, but we have validated the hostname.
    # We proceed to call transport with the original URL.
    
    try:
        status, headers, body = transport(url)
    except Exception as e:
        raise ValueError(f"Transport failed: {e}")
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Return body
    return body
