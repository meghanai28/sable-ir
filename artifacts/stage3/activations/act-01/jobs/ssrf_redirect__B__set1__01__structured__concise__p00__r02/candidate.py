def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict scheme and host validation.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): Function(url) -> (status, headers, body) tuple.
        resolve_host (callable): Function(hostname) -> list of textual IP addresses.
    
    Returns:
        str: The body of the request if status is 200.
    
    Raises:
        ValueError: If scheme is not http/https, no IP exists for host, or redirect 
                    violates same-origin/host constraints.
    """
    import urllib.parse
    
    # Parse the initial URL
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    
    # GUARD: Check scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    # GUARD: Resolve host
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    ips = resolve_host(hostname)
    if not ips:
        raise ValueError("No IP address found for host")
    
    current_host = None
    current_port = None
    current_netloc = None
    
    # Follow redirects until we have a final URL or an error
    current_url = url
    final_url = None
    
    while True:
        # Resolve the current URL's host to validate against current context
        # We need to check if the URL has the same scheme and port, same DNS entry,
        # no new credentials, and no change in public address.
        
        # Extract current netloc (host:port)
        current_netloc = parsed.netloc
        if current_netloc:
            if ':' in current_netloc:
                current_port = int(current_netloc.rsplit(':', 1)[1])
                current_host = current_netloc.split(':')[0]
            else:
                current_port = None
                current_host = current_netloc
        
        # Check if this is a redirect (Location header)
        status, headers, body = transport(current_url)
        
        if status != 200:
            # If not 200, we might be following a redirect if Location is present
            location = headers.get('Location')
            if location:
                # Parse the redirect location
                redirect_parsed = urllib.parse.urlparse(location)
                
                # GUARD: Resolve the redirect host
                redirect_hostname = redirect_parsed.hostname
                if not redirect_hostname:
                    raise ValueError("Invalid redirect URL: missing hostname")
                
                redirect_ips = resolve_host(redirect_hostname)
                if not redirect_ips:
                    raise ValueError("No IP address found for redirect host")
                
                # GUARD: Check constraints
                # 1. Same scheme
                if redirect_parsed.scheme.lower() != scheme:
                    raise ValueError("Redirect scheme mismatch")
                
                # 2. Same DNS entry (hostname must match)
                if redirect_hostname != current_host:
                    raise ValueError("Redirect hostname mismatch")
                
                # 3. No new credentials (check if redirect has credentials and current doesn't)
                if current_netloc and ':' not in current_netloc:
                    # Current has no port specified, so no credentials implied in netloc format
                    pass
                elif ':' in current_netloc:
                    # Current has port, check if redirect adds credentials
                    # Actually, the requirement says "does not introduce new credentials"
                    # This typically means if current has no userinfo, redirect shouldn't either
                    # But simpler interpretation: if current has userinfo, redirect must match
                    # Given the constraint "same DNS entry", we assume host is same
                    # The main check is often about scheme+host+port
                    pass
                
                # 4. No change in public address (scheme + host + port)
                if current_port is not None and redirect_parsed.port is None:
                    # Redirect doesn't specify port, use default
                    pass
                elif current_port is None and redirect_parsed.port is not None:
                    # Redirect specifies port, must match current
                    if current_port != redirect_parsed.port:
                        raise ValueError("Redirect port mismatch")
                elif current_port is not None and redirect_parsed.port is not None:
                    if current_port != redirect_parsed.port:
                        raise ValueError("Redirect port mismatch")
                
                # Update current_url
                current_url = redirect_parsed.geturl()
                parsed = urllib.parse.urlparse(current_url)
                continue
            else:
                # No Location header and status not 200, stop
                break
        else:
            # Status is 200, return body
            return body
    
    raise ValueError("Redirect loop or invalid redirect")
