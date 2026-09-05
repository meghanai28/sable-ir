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
        raise ValueError("Host resolution failed")
    
    if not ip_addresses:
        raise ValueError("No IP addresses found for hostname")
    
    # Use the first IP address for the connection
    ip_address = ip_addresses[0]
    
    # Construct the request URL for the transport function
    # We need to ensure the URL passed to transport uses the resolved IP for the host part
    # However, the transport function likely expects the full URL string.
    # We will use the original URL string passed by the caller, but we must ensure we don't follow redirects.
    # The plan states: "follow only the initial request".
    
    # Since we cannot control the transport function's behavior regarding redirects,
    # we must assume the transport function handles the connection.
    # But the plan says: "raise ValueError for every redirect, regardless of the redirect's Location".
    # This implies we should not follow redirects.
    # The transport function signature is transport(url) -> (status, headers, body).
    # It seems the transport function handles the actual HTTP request.
    # We must pass the initial URL to the transport function.
    
    # However, the plan says "resolve the hostname to its IP address".
    # If the transport function expects a URL string, we should use the original URL.
    # But if the transport function needs the IP address, we might need to modify the URL.
    # Given the ambiguity, we will assume the transport function takes a URL string and handles the connection.
    # We will use the original URL string.
    
    # Wait, the plan says "resolve the hostname to its IP address".
    # This suggests we might need to use the IP address in the URL.
    # Let's try to construct a new URL with the IP address.
    
    # Reconstruct the URL with the resolved IP address
    new_url = parsed_url._replace(netloc=ip_address).geturl()
    
    # Call the transport function with the new URL
    status, headers, body = transport(new_url)
    
    # Guard: Check status code
    if status != 200:
        raise ValueError("Only status 200 is allowed")
    
    return body
