def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL using the provided transport and host resolver.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The response body text for status 200.
    
    Raises:
        ValueError: If the hostname cannot be resolved, the port is invalid, or the status is not 200.
    """
    import urllib.parse
    
    # Parse the URL to extract scheme, netloc, and path
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc
    path = parsed.path
    
    # Validate scheme and port
    if scheme not in ['http', 'https']:
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    port = parsed.port
    if port is None:
        if scheme == 'http':
            port = 80
        elif scheme == 'https':
            port = 443
    else:
        if scheme == 'http' and port != 80:
            raise ValueError("HTTP requests must use port 80.")
        if scheme == 'https' and port != 443:
            raise ValueError("HTTPS requests must use port 443.")
    
    # Resolve hostname
    hostname = netloc.split(':')[0]
    if not resolve_host(hostname):
        raise ValueError(f"Cannot resolve hostname: {hostname}")
    
    # Construct the URL string with the resolved port for transport
    if port == 80:
        url_str = f"{scheme}://{netloc}"
    else:
        url_str = f"{scheme}://{netloc}:{port}"
    
    # Fetch the response
    status, headers, body = transport(url_str)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Handle redirects
    location = headers.get('Location')
    while location:
        # Parse the location header
        location_parsed = urllib.parse.urlparse(location)
        
        # Check if the location is an absolute URL
        if not location_parsed.scheme or not location_parsed.netloc:
            raise ValueError("Redirect must be an absolute URL.")
        
        # Resolve the new hostname
        new_hostname = location_parsed.netloc.split(':')[0]
        if not resolve_host(new_hostname):
            raise ValueError(f"Cannot resolve hostname in redirect: {new_hostname}")
        
        # Check if the path remains beneath the requested URL's directory
        # We need to ensure the new path is a subpath of the original path
        original_path = urllib.parse.urlparse(url).path
        if not original_path.endswith('/'):
            original_path += '/'
        
        # Normalize paths to compare
        if not location_parsed.path.startswith(original_path):
            raise ValueError("Redirect path must remain beneath the requested URL's directory.")
        
        # Update the base URL for the next iteration
        url_str = f"{location_parsed.scheme}://{location_parsed.netloc}{location_parsed.path}"
        location = headers.get('Location')
    
    # Return the body text
    return body.decode('utf-8') if isinstance(body, bytes) else str(body)
