def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security validations.
    
    Args:
        url: The URL to fetch (may be absolute or relative).
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status code 200.
    
    Raises:
        ValueError: If the URL is disallowed, hostname resolution fails, or redirects violate rules.
    """
    import urllib.parse
    import socket
    import re
    
    # Helper to validate hostname (basic check for valid characters)
    def is_valid_hostname(hostname):
        if not hostname or not isinstance(hostname, str):
            return False
        # Allow alphanumeric, hyphens, dots, and underscores
        return bool(re.match(r'^[a-zA-Z0-9\-\._]+$', hostname))
    
    # Helper to validate IP address (basic check)
    def is_valid_ip(ip):
        if not ip or not isinstance(ip, str):
            return False
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        for part in parts:
            if not part.isdigit():
                return False
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    
    # Helper to validate public address (basic check for no internal ranges)
    def is_public_address(ip):
        # Block private ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, ::1)
        if is_valid_ip(ip):
            parts = ip.split('.')
            if len(parts) == 4:
                try:
                    first = int(parts[0])
                    second = int(parts[1])
                    # 10.x.x.x
                    if first == 10:
                        return False
                    # 172.16.x.x - 172.31.x.x
                    if first == 172 and 16 <= second <= 31:
                        return False
                    # 192.168.x.x
                    if first == 192 and second == 168:
                        return False
                    # 127.x.x.x (loopback)
                    if first == 127:
                        return False
                except ValueError:
                    pass
        return True
    
    # Parse the initial URL
    try:
        parsed_url = urllib.parse.urlparse(url)
    except Exception:
        raise ValueError("Invalid URL format")
    
    scheme = parsed_url.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Check for absolute URLs (should already be handled by urlparse, but extra guard)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError("Absolute URL required")
    
    # Resolve hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid hostname")
    
    if not is_valid_hostname(hostname):
        raise ValueError("Invalid hostname characters")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Hostname resolution failed")
    
    # Validate at least one IP
    valid_ip = False
    for ip in ip_addresses:
        if is_valid_ip(ip):
            valid_ip = True
            break
    if not valid_ip:
        raise ValueError("No valid IP addresses found")
    
    # Check for public address (block private IPs)
    public_ip = None
    for ip in ip_addresses:
        if is_public_address(ip):
            public_ip = ip
            break
    
    if not public_ip:
        raise ValueError("Only public addresses are allowed")
    
    # Check scheme and port before starting connection
    if scheme == 'http':
        port = 80
    else:
        port = 443
    
    if parsed_url.port:
        if parsed_url.port != port:
            raise ValueError("Port mismatch")
    else:
        parsed_url = parsed_url._replace(port=port)
    
    # Build the initial full URL
    initial_url = parsed_url._replace(path=url).geturl()
    
    # Validate initial URL components
    if not initial_url.startswith('http://') and not initial_url.startswith('https://'):
        raise ValueError("Invalid URL scheme")
    
    # Process redirects (at most 5 hops)
    current_url = initial_url
    hop_count = 0
    max_hops = 5
    
    while hop_count < max_hops:
        # Parse current URL
        try:
            current_parsed = urllib.parse.urlparse(current_url)
        except Exception:
            raise ValueError("Invalid URL format")
        
        # Check scheme and port consistency
        if current_parsed.scheme != scheme:
            raise ValueError("Scheme mismatch in redirect")
        
        if current_parsed.port:
            if current_parsed.port != port:
                raise ValueError("Port mismatch in redirect")
        else:
            current_parsed = current_parsed._replace(port=port)
        
        # Resolve hostname for redirect
        redirect_hostname = current_parsed.hostname
        if not redirect_hostname:
            raise ValueError("Invalid hostname in redirect")
        
        if not is_valid_hostname(redirect_hostname):
            raise ValueError("Invalid hostname characters in redirect")
        
        redirect_ips = resolve_host(redirect_hostname)
        if not redirect_ips:
            raise ValueError("Hostname resolution failed in redirect")
        
        valid_redirect_ip = False
        for ip in redirect_ips:
            if is_valid_ip(ip):
                valid_redirect_ip = True
                break
        if not valid_redirect_ip:
            raise ValueError("No valid IP addresses found in redirect")
        
        redirect_public_ip = None
        for ip in redirect_ips:
            if is_public_address(ip):
                redirect_public_ip = ip
                break
        
        if not redirect_public_ip:
            raise ValueError("Only public addresses are allowed in redirect")
        
        # Check for unsafe path components (.. segments)
        path = current_parsed.path
        if path:
            # Normalize path to check for ..
            normalized_path = urllib.parse.unquote(path)
            if '..' in normalized_path:
                raise ValueError("Unsafe path segments detected")
        
        # Check for absolute path (starting with /)
        if path and path.startswith('/'):
            raise ValueError("Absolute path not allowed")
        
        # Construct the next URL (handling query and fragment)
        next_url = current_parsed._replace(path=path).geturl()
        
        # Call transport
        try:
            status, headers, body = transport(current_url)
        except Exception:
            raise ValueError("Transport error")
        
        # Check status code
        if status != 200:
            raise ValueError("Unexpected status code")
        
        # Check for Location header (redirect)
        location_header = headers.get('Location')
        if location_header:
            hop_count += 1
            if hop_count >= max_hops:
                raise ValueError("Too many redirects")
            
            # Parse Location
            try:
                location_parsed = urllib.parse.urlparse(location_header)
            except Exception:
                raise ValueError("Invalid Location header")
            
            # Check if it's an absolute URL
            if location_parsed.scheme:
                next_url = location_header
            else:
                # Relative URL - resolve against current URL
                base_url = urllib.parse.urlparse(current_url)
                if not location_header.startswith(('http://', 'https://')):
                    next_url = urllib.parse.urljoin(base_url.geturl(), location_header)
                else:
                    next_url = location_header
            
            # Ensure the next URL has the same scheme and port
            if not next_url.startswith('http://') and not next_url.startswith('https://'):
                raise ValueError("Invalid redirect URL")
            
            if location_parsed.scheme != scheme:
                raise ValueError("Scheme mismatch in redirect")
            
            if location_parsed.port:
                if location_parsed.port != port:
                    raise ValueError("Port mismatch in redirect")
            else:
                location_parsed = location_parsed._replace(port=port)
            
            current_url = next_url
        else:
            break
    
    return body
