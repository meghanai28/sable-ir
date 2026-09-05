def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL by resolving the host, opening the file, and returning the body.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The body of the response for status 200.
    
    Raises:
        ValueError: If the request is disallowed.
    """
    # Parse the URL to extract the hostname and path
    from urllib.parse import urlparse
    
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    path = parsed_url.path
    
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    # Resolve the host to get IP addresses
    ip_addresses = resolve_host(hostname)
    
    if not ip_addresses:
        raise ValueError("No IP addresses found for the hostname")
    
    # Determine the port
    port = parsed_url.port
    if port is None:
        port = 80 if parsed_url.scheme == "http" else 443
    
    # Use the first IP address for the request
    ip_address = ip_addresses[0]
    
    # Construct the full URL with the resolved IP
    if port == 80 and parsed_url.scheme == "http":
        full_url = f"http://{ip_address}{path}"
    elif port == 443 and parsed_url.scheme == "https":
        full_url = f"https://{ip_address}{path}"
    else:
        full_url = f"{parsed_url.scheme}://{ip_address}:{port}{path}"
    
    # Make the request using the transport function
    status, headers, body = transport(full_url)
    
    # Check the status code
    if status != 200:
        raise ValueError(f"Invalid status code: {status}")
    
    # Return the body as a string
    return body
