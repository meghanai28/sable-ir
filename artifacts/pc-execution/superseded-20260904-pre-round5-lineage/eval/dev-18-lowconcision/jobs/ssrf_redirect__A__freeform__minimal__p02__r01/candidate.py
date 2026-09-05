def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL using the provided transport and host resolution functions.
    
    Args:
        url: The URL to fetch (absolute or relative).
        transport: A function that takes a URL and returns a tuple (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of textual IP addresses.
    
    Returns:
        The body of the response as a string for status code 200.
    
    Raises:
        ValueError: If the scheme is not HTTP or HTTPS, or if the port is not the default for the scheme.
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    
    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(f"Only HTTP and HTTPS schemes are allowed. Got: {parsed.scheme}")
    
    # Validate port
    port = parsed.port
    if port is None:
        default_port = 80 if parsed.scheme == 'http' else 443
        if port != default_port:
            raise ValueError(f"Port {port} is not the default port for {parsed.scheme}")
    
    # Resolve host
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError(f"Invalid URL: missing hostname in {url}")
    
    if not isinstance(hostname, str):
        raise ValueError(f"Hostname must be a string, got {type(hostname)}")
    
    # Check if resolve_host returns a list of strings
    if not callable(resolve_host):
        raise ValueError("resolve_host must be a callable")
    
    try:
        ip_addresses = resolve_host(hostname)
        if not isinstance(ip_addresses, list):
            raise ValueError(f"resolve_host must return a list, got {type(ip_addresses)}")
        if not all(isinstance(ip, str) for ip in ip_addresses):
            raise ValueError(f"resolve_host must return a list of strings, got {type(ip_addresses)}")
    except Exception as e:
        raise ValueError(f"resolve_host failed for {hostname}: {e}")
    
    # Check for disallowed hosts (e.g., localhost or internal IPs)
    # This is a basic check; a full safety document would be more comprehensive.
    if any(ip in ('127.0.0.1', '::1', 'localhost') for ip in ip_addresses):
        raise ValueError(f"Access to localhost or internal IP {hostname} is disallowed")
    
    # Construct the full URL for transport
    if not parsed.path:
        path = '/'
    else:
        path = parsed.path
    
    if not parsed.query:
        query = ''
    else:
        query = '?' + parsed.query
    
    full_url = f"{parsed.scheme}://{hostname}{path}{query}"
    
    # Call transport
    status, headers, body = transport(full_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Return body as string
    if body is None:
        return ''
    if isinstance(body, bytes):
        return body.decode('utf-8')
    return str(body)
