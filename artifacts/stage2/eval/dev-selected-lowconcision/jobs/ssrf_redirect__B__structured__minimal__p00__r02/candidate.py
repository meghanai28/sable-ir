def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL using the provided transport and host resolver.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The response body for a 200 status code.
    
    Raises:
        ValueError: If the scheme is not http or https, or if no valid IP addresses are resolved.
    """
    from urllib.parse import urlparse
    
    # Parse the URL to check the scheme
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme.lower()
    
    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Resolve hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname.")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError(f"No valid IP addresses resolved for {hostname}.")
    
    # Build the request URL with the resolved IP (or use the original if multiple, typically first)
    # The transport function expects a URL, so we use the original URL string but ensure we don't pass
    # the IP list directly. The plan says transport(url) returns (status, headers, body).
    # We assume transport handles the connection logic.
    
    status, headers, body = transport(url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Request failed with status code {status}.")
    
    return body
