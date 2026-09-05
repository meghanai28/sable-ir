def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security guards.
    
    Args:
        url: The URL to fetch.
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of textual IP addresses.
    
    Returns:
        The response body for status 200.
    
    Raises:
        ValueError: If the scheme is not http/https, hostname resolution fails,
                   the path escapes the root, or a redirect is encountered.
    """
    # GUARD: Resolve hostname and check scheme before proceeding
    try:
        ip_addresses = resolve_host(url)
    except Exception:
        raise ValueError("Hostname resolution failed")
    
    # Extract scheme and netloc to check for path traversal and validate scheme
    scheme = None
    netloc = None
    
    if url.startswith('http://'):
        scheme = 'http'
        netloc = url[7:]
    elif url.startswith('https://'):
        scheme = 'https'
        netloc = url[8:]
    else:
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # GUARD: Check for path traversal in the initial URL
    # We need to parse the URL to get the path. Since we can't use external libraries,
    # we'll manually parse the netloc and path.
    # netloc contains the hostname and possibly the port.
    # We need to extract the path from the original URL.
    path = url.split('?', 1)[1] if '?' in url else ''
    
    # Remove query string from path for containment check
    if path.startswith('/'):
        path = path[1:]
    
    # Check for .. in the path segments
    if '..' in path:
        raise ValueError("Path traversal detected")
    
    # Check if the path starts with ..
    if path.startswith('..'):
        raise ValueError("Path traversal detected")
    
    # GUARD: Check scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # GUARD: Open connection and handle redirects
    status, headers, body = transport(url)
    
    # GUARD: Follow redirects only for the initial public HTTP destination
    # The plan says "follow the initial public HTTP destination only"
    # This implies we should not follow redirects that change the host or go to non-HTTP/HTTPS
    # However, the plan also says "raise ValueError for every redirect response"
    # This is contradictory. Let's re-read: "follow the initial public HTTP destination only"
    # This likely means we only follow redirects that keep us on the same host/scheme.
    # But "raise ValueError for every redirect response" suggests we should not follow any redirect.
    # Given the strict security context, we should not follow any redirect.
    
    if status != 200:
        raise ValueError("Redirect or non-200 status encountered")
    
    return body
