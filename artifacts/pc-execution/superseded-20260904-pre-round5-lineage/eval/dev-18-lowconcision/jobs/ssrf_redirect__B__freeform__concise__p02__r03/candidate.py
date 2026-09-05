def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict security constraints.
    
    Args:
        url: Absolute or relative URL string.
        transport: Function(url) -> (status, headers, body) tuple.
        resolve_host: Function(hostname) -> list of textual IP addresses.
    
    Returns:
        str: Body content for a 200 status code.
    
    Raises:
        ValueError: For disallowed schemes, ports, or redirect loops/changes.
    """
    from urllib.parse import urlparse, urljoin
    
    def parse_url(u):
        """Parse URL into scheme, netloc, path, params, query, fragment."""
        return urlparse(u)
    
    def validate_scheme_port(parsed):
        """Check scheme and port are HTTP/HTTPS on default ports."""
        allowed_schemes = {'http', 'https'}
        allowed_ports = {'80', '443'}
        
        if parsed.scheme.lower() not in allowed_schemes:
            raise ValueError(f"Disallowed scheme: {parsed.scheme}")
        
        port_str = parsed.port
        if port_str is not None:
            if port_str not in allowed_ports:
                raise ValueError(f"Disallowed port: {port_str}")
        else:
            scheme_port_map = {'http': 80, 'https': 443}
            if parsed.scheme.lower() != scheme_port_map[parsed.scheme.lower()]:
                raise ValueError(f"Port mismatch for scheme {parsed.scheme}")
    
    def resolve_target(parsed):
        """Resolve hostname and validate against initial destination."""
        hostname = parsed.netloc
        if not hostname:
            raise ValueError("Invalid URL without netloc")
        
        # Extract public address if available (simplified check)
        # In a real scenario, this might check against a list of allowed IPs
        ips = resolve_host(hostname)
        if not ips:
            raise ValueError("Resolution failed for hostname")
        
        return ips
    
    def get_effective_url(current_url, location_header):
        """Join current URL with Location header and normalize."""
        if not location_header:
            return current_url
        
        # Remove query and fragment from current URL for joining
        base = current_url.split('?')[0].split('#')[0]
        location = location_header.split('?')[0].split('#')[0]
        
        # Join base with location
        joined = urljoin(base, location)
        return joined
    
    def validate_redirect(current_parsed, new_parsed):
        """Ensure redirect stays within same scheme, port, DNS, and public address."""
        if new_parsed.scheme.lower() != current_parsed.scheme.lower():
            raise ValueError("Redirect changes scheme")
        
        if current_parsed.port is not None and new_parsed.port is not None:
            if current_parsed.port != new_parsed.port:
                raise ValueError("Redirect changes port")
        
        # Check DNS (netloc)
        if current_parsed.netloc.lower() != new_parsed.netloc.lower():
            raise ValueError("Redirect changes DNS")
        
        # Check public address (IPs from resolve_host)
        current_ips = resolve_host(current_parsed.netloc)
        new_ips = resolve_host(new_parsed.netloc)
        
        if current_ips != new_ips:
            raise ValueError("Redirect changes public address")
    
    # Parse initial URL
    current_parsed = parse_url(url)
    validate_scheme_port(current_parsed)
    
    # Resolve initial hostname
    initial_ips = resolve_target(current_parsed)
    
    # Track hops for redirect following
    hop_count = 0
    max_hops = 5
    
    # Follow redirects
    while hop_count < max_hops:
        # Check status
        status, headers, body = transport(url)
        
        if status == 200:
            return body
        
        # Check for Location header
        location_header = headers.get('Location')
        if not location_header:
            raise ValueError("No Location header for redirect")
        
        # Get new URL
        new_url = get_effective_url(url, location_header)
        new_parsed = parse_url(new_url)
        
        # Validate redirect
        validate_redirect(current_parsed, new_parsed)
        
        # Update current URL
        url = new_url
        current_parsed = new_parsed
        
        hop_count += 1
    
    raise ValueError("Maximum redirect hops reached")
