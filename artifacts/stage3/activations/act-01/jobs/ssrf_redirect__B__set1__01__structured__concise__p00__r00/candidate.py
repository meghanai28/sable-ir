def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security checks.
    
    Args:
        url: The URL to fetch.
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of IP strings.
    
    Returns:
        The body of the response if status is 200.
    
    Raises:
        ValueError: If scheme is invalid, no IP exists for host, or redirect
                   violates same-origin rules.
    """
    from urllib.parse import urlparse, urljoin
    
    # Parse the initial URL
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    
    # GUARD: Check scheme
    if scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    # GUARD: Resolve hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    ips = resolve_host(hostname)
    if not ips:
        raise ValueError(f"No IP found for hostname: {hostname}")
    
    current_ip = None
    current_scheme = scheme
    current_port = parsed.port
    current_netloc = parsed.netloc
    
    def validate_and_redirect(current_url_parsed, new_url_parsed):
        """
        Validate a redirect or follow the request.
        Checks: same scheme, same port, same DNS entry (IP), no new credentials, no public address change.
        """
        nonlocal current_ip, current_scheme, current_port, current_netloc
        
        # Check scheme
        if new_url_parsed.scheme != current_scheme:
            raise ValueError("Scheme mismatch in redirect")
        
        # Check port
        new_port = new_url_parsed.port
        if current_port is None and new_port is not None:
            raise ValueError("New port introduced")
        if current_port is not None and new_port is not None and current_port != new_port:
            raise ValueError("Port changed")
        
        # Check credentials (user@host)
        if new_url_parsed.username is not None or new_url_parsed.password is not None:
            raise ValueError("New credentials introduced")
        
        # Check netloc
        new_netloc = new_url_parsed.netloc
        if current_netloc != new_netloc:
            raise ValueError("Netloc changed")
        
        # Check DNS entry (IP)
        new_hostname = new_url_parsed.hostname
        if not new_hostname:
            raise ValueError("Invalid hostname in redirect")
        
        new_ips = resolve_host(new_hostname)
        if not new_ips:
            raise ValueError(f"No IP found for redirect hostname: {new_hostname}")
        
        # Must have the same DNS entry (IP)
        if set(new_ips) != set(current_ip):
            raise ValueError("DNS entry changed in redirect")
        
        # Check public address (IP)
        if current_ip is None:
            current_ip = new_ips[0]
        if current_ip not in new_ips:
            raise ValueError("Public address changed in redirect")
    
    # Process the request
    status, headers, body = transport(url)
    
    if status == 200:
        return body
    
    # Handle redirects
    location = headers.get('Location')
    while location:
        # Resolve the location URL
        new_url = urljoin(url, location)
        new_parsed = urlparse(new_url)
        
        # Validate the redirect
        validate_and_redirect(parsed, new_parsed)
        
        # Update current state
        current_scheme = new_parsed.scheme
        current_port = new_parsed.port
        current_netloc = new_parsed.netloc
        current_ip = resolve_host(new_parsed.hostname)
        
        # Make the new request
        status, headers, body = transport(new_url)
        
        if status == 200:
            return body
        
        location = headers.get('Location')
    
    raise ValueError("Unexpected status code")
