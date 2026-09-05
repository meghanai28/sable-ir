def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security guards.
    
    Args:
        url: The target URL string.
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of textual IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If scheme/port is disallowed, path escapes, or DNS looks suspicious.
    """
    from urllib.parse import urlparse, urljoin, urlunparse
    
    # Parse the source URL
    source_parsed = urlparse(url)
    scheme = source_parsed.scheme
    port = source_parsed.port
    hostname = source_parsed.hostname
    
    # GUARD: Check scheme and port
    # Default ports: HTTP=80, HTTPS=443. We reject these.
    disallowed_schemes = {'http', 'https'}
    if scheme in disallowed_schemes:
        default_port = 80 if scheme == 'http' else 443
        if port == default_port:
            raise ValueError("Disallowed default port for scheme")
    
    # Check for DNS rebind (embedded DNS segment)
    if hostname:
        # Simple check: if hostname looks like an IP, raise error
        # The prompt says "do not start with an embedded DNS segment", implying we reject
        # hostnames that resolve to IPs or contain IP-like structures that might be
        # used for DNS rebind attacks. A safe interpretation for a generic
        # "textual IP addresses" check is to ensure the resolved IPs don't
        # look like they were intended to be the hostname (DNS rebind).
        # However, the prompt says "raise ValueError unless its textual IP addresses
        # do not start with an embedded DNS segment". This is slightly ambiguous.
        # A common interpretation in such constraints is to ensure the hostname
        # is not an IP address itself (which would be resolved to itself) or
        # that the resolution process isn't trivially bypassing DNS.
        # Let's assume the requirement is to reject if the resolved IPs are
        # identical to the hostname (DNS rebind check) or if the hostname
        # is an IP address.
        resolved_ips = resolve_host(hostname)
        if resolved_ips and resolved_ips[0] == hostname:
            raise ValueError("DNS rebind detected: resolved IP matches hostname")
    
    # ORDER: Check scheme and port before creating request
    # (Already done in GUARD)
    
    # We need to handle redirects. The plan says "follow at most five hops".
    # We need the referring URL to check path traversal.
    # Since we don't have a referring URL in the args, we assume the current
    # URL is the base for the check, or we need to handle the redirect chain
    # carefully. The plan says "join the requested URL with the referring URL".
    # Without a referring URL, we might assume the initial URL is the base
    # or that the "referring" concept applies to the redirect chain.
    # Let's assume the initial URL is the base for the path check.
    
    # Parse the target URL
    target_parsed = urlparse(url)
    path = target_parsed.path
    
    # Check for path traversal (..)
    if '..' in path:
        raise ValueError("Path traversal detected")
    
    # Handle redirects
    # We need to track the chain of URLs to limit hops and check path traversal.
    # The plan implies we follow redirects.
    # We'll use a stack or list to track visited URLs.
    visited_urls = []
    current_url = url
    hop_count = 0
    
    while hop_count < 5:
        # Check path traversal for the current URL in the chain
        parsed = urlparse(current_url)
        if '..' in parsed.path:
            raise ValueError("Path traversal detected in redirect chain")
        
        # Check if we've visited this URL before (loop detection)
        if current_url in visited_urls:
            raise ValueError("Redirect loop detected")
        visited_urls.append(current_url)
        
        # Make the request
        status, headers, body = transport(current_url)
        
        if status == 301 or status == 302:
            # Parse Location header
            location = headers.get('Location')
            if not location:
                raise ValueError("Missing Location header in redirect")
            # Join current URL with Location
            new_url = urljoin(current_url, location)
            current_url = new_url
            hop_count += 1
        else:
            break
    
    # Final check: status must be exactly 200
    if status != 200:
        raise ValueError("Expected status 200, got {}".format(status))
    
    # Return the body
    return body
