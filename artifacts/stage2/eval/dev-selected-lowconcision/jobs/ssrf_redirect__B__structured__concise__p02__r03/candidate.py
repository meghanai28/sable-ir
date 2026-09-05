def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security guards against open redirect and unsafe schemes.
    
    Args:
        url: The target URL string.
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of IP address strings.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the scheme is not http/https, no IP is found, or redirect violates constraints.
    """
    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, unquote
    
    def validate_scheme(url_str):
        parsed = urlparse(url_str)
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError(f"Disallowed scheme: {scheme}")
        return parsed
    
    def resolve_target(parsed, location_url=None):
        """Resolve hostname to IPs and validate against initial destination."""
        if location_url is None:
            location_url = parsed.geturl()
        
        target_parsed = urlparse(location_url)
        
        # Extract hostname for resolution
        hostname = target_parsed.hostname
        if not hostname:
            raise ValueError("Invalid URL: no hostname found")
        
        # Resolve hostname
        ips = resolve_host(hostname)
        if not ips:
            raise ValueError(f"No IP found for hostname: {hostname}")
        
        # Validate constraints:
        # 1. Scheme must match
        if target_parsed.scheme != parsed.scheme:
            raise ValueError(f"Redirect scheme mismatch: {target_parsed.scheme} != {parsed.scheme}")
        
        # 2. Port must match (or be default if not specified in initial)
        initial_port = parsed.port
        target_port = target_parsed.port
        if initial_port is not None and target_port != initial_port:
            raise ValueError(f"Redirect port mismatch: {target_port} != {initial_port}")
        
        # 3. Credentials must match (username/password)
        if parsed.username or parsed.password:
            if target_parsed.username != parsed.username or target_parsed.password != parsed.password:
                raise ValueError("Redirect credentials mismatch")
        
        # 4. DNS and public address must match
        # We compare the list of resolved IPs. The set of IPs must be identical.
        initial_ips = set(ips)
        target_ips = set(resolve_host(target_parsed.hostname))
        if initial_ips != target_ips:
            raise ValueError(f"DNS/IP mismatch: {initial_ips} != {target_ips}")
        
        return target_parsed.geturl()
    
    def is_safe_redirect(current_parsed, location_url):
        """Check if redirect is safe according to plan constraints."""
        # Parse the redirect location
        redirect_parsed = urlparse(location_url)
        
        # Scheme must match
        if redirect_parsed.scheme != current_parsed.scheme:
            return False
        
        # Port must match
        if current_parsed.port is not None and redirect_parsed.port != current_parsed.port:
            return False
        
        # Credentials must match
        if current_parsed.username or current_parsed.password:
            if redirect_parsed.username != current_parsed.username or redirect_parsed.password != current_parsed.password:
                return False
        
        # DNS and public address must match
        # Get the hostname to resolve
        hostname = redirect_parsed.hostname
        if not hostname:
            return False
        
        # Resolve both
        current_ips = set(resolve_host(current_parsed.hostname))
        redirect_ips = set(resolve_host(hostname))
        
        if current_ips != redirect_ips:
            return False
        
        return True
    
    # Initial parsing
    initial_parsed = validate_scheme(url)
    initial_scheme = initial_parsed.scheme
    initial_host = initial_parsed.hostname
    initial_port = initial_parsed.port
    initial_credentials = (initial_parsed.username, initial_parsed.password)
    initial_ips = set(resolve_host(initial_host)) if initial_host else set()
    
    current_url = url
    current_parsed = initial_parsed
    redirect_count = 0
    max_redirects = 5
    
    while True:
        # Get response
        status, headers, body = transport(current_url)
        
        # Check status
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Check for redirect
        location = headers.get('Location')
        if location:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError(f"Too many redirects: {redirect_count}")
            
            # Resolve and validate the redirect target
            resolved_location = resolve_target(current_parsed, location)
            
            # Safety check: ensure it's safe
            if not is_safe_redirect(current_parsed, location):
                raise ValueError("Redirect violates security constraints")
            
            current_url = resolved_location
            current_parsed = urlparse(current_url)
        else:
            break
        
        # Update current_parsed for next iteration
        current_parsed = urlparse(current_url)
    
    # Return body
    return body
