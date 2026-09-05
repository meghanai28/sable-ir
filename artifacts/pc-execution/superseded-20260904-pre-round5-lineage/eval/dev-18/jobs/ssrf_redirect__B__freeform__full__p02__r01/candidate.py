def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security constraints.
    
    Args:
        url: The target URL (absolute or relative).
        transport: A callable(url) -> (status, headers, body) tuple.
        resolve_host: A callable(hostname) -> list of textual IP addresses.
    
    Returns:
        The body of a successful request (status 200) as a string.
    
    Raises:
        ValueError: For disallowed schemes, hop limit exceeded, or unsafe redirects.
    """
    import urllib.parse
    import socket
    
    # Helper to normalize URL and get scheme, port, credentials, host, path
    def parse_url_info(url_str):
        parsed = urllib.parse.urlparse(url_str)
        scheme = parsed.scheme.lower()
        port = parsed.port
        # Default ports
        if scheme == 'http':
            default_port = 80
        elif scheme == 'https':
            default_port = 443
        else:
            default_port = None
        
        # Validate scheme
        if scheme not in ('http', 'https'):
            raise ValueError(f"Disallowed scheme: {scheme}")
        
        # Validate port
        if port is not None and port != default_port:
            raise ValueError(f"Non-default port {port} not allowed for {scheme}")
        
        # Resolve host
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError(f"Invalid hostname in URL: {url_str}")
        
        try:
            ip_addresses = resolve_host(hostname)
        except Exception:
            raise ValueError(f"Failed to resolve host: {hostname}")
        
        if not ip_addresses:
            raise ValueError(f"No IP addresses found for host: {hostname}")
        
        # Check for DNS manipulation (same public address)
        # The requirement says "same scheme, port, credentials, DNS, and public address"
        # We assume the initial resolution is trusted, so subsequent ones must match.
        # We'll store the resolved IP list from the initial request.
        return {
            'scheme': scheme,
            'port': port,
            'credentials': parsed.username + ':' + parsed.password if parsed.username or parsed.password else None,
            'dns': hostname,
            'public_address': ip_addresses[0], # Using first IP as representative
            'path': parsed.path,
            'query': parsed.query,
            'fragment': parsed.fragment
        }

    # Parse initial URL
    initial_info = parse_url_info(url)
    initial_scheme = initial_info['scheme']
    initial_port = initial_info['port']
    initial_credentials = initial_info['credentials']
    initial_dns = initial_info['dns']
    initial_public_address = initial_info['public_address']
    initial_path = initial_info['path']
    initial_query = initial_info['query']
    
    # Start fetching
    current_url = url
    hops = 0
    max_hops = 5
    
    while hops <= max_hops:
        # If not the first hop, we are following a redirect
        if hops > 0:
            # Check scheme, port, credentials, DNS, and public address
            # Note: The plan says "same scheme, port, credentials, DNS, and public address"
            # We compare against the initial destination's resolved info.
            # However, typically redirects preserve these. We must ensure strict equality.
            
            # Re-parse current_url to get relative parts if needed, but we need full info
            # Actually, the transport returns the full URL for the request, but we need to check
            # the properties of the *destination* of the redirect.
            # The plan says: "each resolved Location must have the same scheme, port, credentials, DNS, and public address as the initial destination"
            
            current_parsed = urllib.parse.urlparse(current_url)
            current_scheme = current_parsed.scheme.lower()
            current_port = current_parsed.port
            current_credentials = current_parsed.username + ':' + current_parsed.password if current_parsed.username or current_parsed.password else None
            current_dns = current_parsed.hostname
            current_public_address = None
            
            # Resolve current hostname
            if current_dns is None:
                raise ValueError(f"Invalid hostname in redirect URL: {current_url}")
            
            try:
                current_ips = resolve_host(current_dns)
            except Exception:
                raise ValueError(f"Failed to resolve host in redirect: {current_dns}")
            
            if not current_ips:
                raise ValueError(f"No IP addresses found for redirect host: {current_dns}")
            
            current_public_address = current_ips[0]
            
            # Check constraints
            if current_scheme != initial_scheme:
                raise ValueError(f"Redirect scheme mismatch: {current_scheme} != {initial_scheme}")
            if current_port is not None and current_port != initial_port:
                raise ValueError(f"Redirect port mismatch: {current_port} != {initial_port}")
            if current_credentials is not None and current_credentials != initial_credentials:
                raise ValueError(f"Redirect credentials mismatch")
            if current_dns != initial_dns:
                raise ValueError(f"Redirect DNS mismatch: {current_dns} != {initial_dns}")
            if current_public_address != initial_public_address:
                raise ValueError(f"Redirect public address mismatch: {current_public_address} != {initial_public_address}")
        
        # Prepare request URL
        # If relative, join with base. If absolute, use as is.
        # But the plan says "caller-supplied url may be absolute or relative".
        # We assume the first call is absolute.
        # For redirects, the transport likely provides the full absolute URL.
        # We just need to make sure we are constructing the request correctly.
        # Actually, the transport is called with the URL.
        
        # Call transport
        status, headers, body = transport(current_url)
        
        # Check status
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Return body
        return body.decode('utf-8') if isinstance(body, bytes) else body
        
        # If we get here, something is wrong (status != 200)
        # But we need to handle redirects.
        # Check for Location header
        location = None
        for key, value in headers.items():
            if key.lower() == 'location':
                location = value
                break
        
        if location:
            hops += 1
            if hops > max_hops:
                raise ValueError(f"Redirect loop or too many hops: {hops} > {max_hops}")
            current_url = location
        else:
            break
    
    raise ValueError("Unexpected end of request")
