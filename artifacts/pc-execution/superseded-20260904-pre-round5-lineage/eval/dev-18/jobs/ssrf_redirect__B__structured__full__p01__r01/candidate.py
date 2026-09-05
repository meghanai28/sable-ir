def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict validation and redirect handling.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The body text for a successful 200 status code.
    
    Raises:
        ValueError: If the URL is disallowed (e.g., absolute, resolves to an IP, etc.).
    """
    import urllib.parse
    import socket
    import re
    
    # Helper to parse URL components
    def parse_url(url):
        try:
            return urllib.parse.urlparse(url)
        except ValueError:
            raise ValueError("Invalid URL")
    
    # Helper to check if a URL is absolute (has a scheme)
    def is_absolute(url):
        return bool(urllib.parse.urlparse(url).scheme)
    
    # Helper to resolve hostname to IP
    def resolve(hostname):
        try:
            return resolve_host(hostname)
        except Exception:
            return []
    
    # Helper to validate URL structure (no .. segments, etc.)
    def validate_url_structure(parsed_url):
        path = parsed_url.path
        # Check for path traversal
        if '..' in path or path.startswith('/..'):
            return False
        return True
    
    # Helper to get the effective scheme and port from a URL
    def get_scheme_port(parsed_url):
        scheme = parsed_url.scheme.lower()
        port = parsed_url.port
        if port is None:
            if scheme == 'http':
                port = 80
            elif scheme == 'https':
                port = 443
        return scheme, port
    
    # Helper to normalize scheme and port
    def normalize_scheme_port(scheme, port):
        if scheme == 'http':
            if port == 80:
                return 'http', None
            else:
                return 'http', port
        elif scheme == 'https':
            if port == 443:
                return 'https', None
            else:
                return 'https', port
        return scheme, port
    
    # Helper to check if two URLs have the same scheme, port, credentials, and DNS
    def same_scheme_port_credentials_dns(parsed_url1, parsed_url2):
        scheme1, port1 = normalize_scheme_port(parsed_url1.scheme, parsed_url1.port)
        scheme2, port2 = normalize_scheme_port(parsed_url2.scheme, parsed_url2.port)
        
        if scheme1 != scheme2:
            return False
        if port1 != port2:
            return False
        
        # Check credentials
        if parsed_url1.username is not None or parsed_url1.password is not None:
            if parsed_url2.username is None or parsed_url2.password is None:
                return False
            if parsed_url1.username != parsed_url2.username or parsed_url1.password != parsed_url2.password:
                return False
        else:
            if parsed_url2.username is not None or parsed_url2.password is not None:
                return False
        
        # Check DNS (hostname)
        if parsed_url1.hostname != parsed_url2.hostname:
            return False
        
        return True
    
    # Helper to resolve a URL against a base URL
    def resolve_url_against_base(base_url, redirect_url):
        try:
            return urllib.parse.urljoin(base_url, redirect_url)
        except ValueError:
            return redirect_url
    
    # Helper to check if a URL resolves to an IP address
    def resolves_to_ip(parsed_url):
        hostname = parsed_url.hostname
        if hostname is None:
            return False
        ips = resolve(hostname)
        return len(ips) > 0
    
    # Helper to check if a URL is absolute
    def is_absolute_url(parsed_url):
        return bool(parsed_url.scheme)
    
    # Initialize validation state
    initial_parsed_url = None
    current_parsed_url = None
    redirect_count = 0
    max_redirects = 5
    
    # Step 1: Validate initial URL
    try:
        initial_parsed_url = parse_url(url)
    except Exception:
        raise ValueError("Invalid URL")
    
    # Check for absolute URLs
    if is_absolute_url(initial_parsed_url):
        raise ValueError("Absolute URLs are disallowed")
    
    # Validate URL structure
    if not validate_url_structure(initial_parsed_url):
        raise ValueError("URL contains path traversal segments")
    
    # Resolve initial hostname
    initial_hostname = initial_parsed_url.hostname
    if initial_hostname is None:
        raise ValueError("Invalid hostname in URL")
    
    initial_ips = resolve(initial_hostname)
    if not initial_ips:
        raise ValueError("Hostname does not resolve to an IP address")
    
    # Normalize initial scheme and port
    initial_scheme, initial_port = normalize_scheme_port(initial_parsed_url.scheme, initial_parsed_url.port)
    
    # Step 2: Process redirects
    current_parsed_url = initial_parsed_url
    while True:
        # Check redirect count
        if redirect_count >= max_redirects:
            raise ValueError("Too many redirects")
        
        # Make the request
        status, headers, body = transport(current_parsed_url)
        
        # Check status code
        if status != 200:
            raise ValueError(f"Non-200 status code: {status}")
        
        # Check for Location header
        location_header = headers.get('Location')
        if location_header is not None:
            redirect_count += 1
            # Resolve the redirect URL against the current URL
            redirect_url = resolve_url_against_base(current_parsed_url, location_header)
            
            # Parse the redirect URL
            try:
                next_parsed_url = parse_url(redirect_url)
            except Exception:
                raise ValueError("Invalid redirect URL")
            
            # Validate redirect URL structure
            if not validate_url_structure(next_parsed_url):
                raise ValueError("Redirect URL contains path traversal segments")
            
            # Check if the redirect URL is absolute
            if is_absolute_url(next_parsed_url):
                raise ValueError("Redirect URL is absolute")
            
            # Resolve the next hostname
            next_hostname = next_parsed_url.hostname
            if next_hostname is None:
                raise ValueError("Invalid hostname in redirect URL")
            
            next_ips = resolve(next_hostname)
            if not next_ips:
                raise ValueError("Redirect hostname does not resolve to an IP address")
            
            # Normalize the next scheme and port
            next_scheme, next_port = normalize_scheme_port(next_parsed_url.scheme, next_parsed_url.port)
            
            # Check if the next URL has the same scheme, port, credentials, and DNS as the initial destination
            if not same_scheme_port_credentials_dns(initial_parsed_url, next_parsed_url):
                raise ValueError("Redirect URL does not match initial destination scheme, port, credentials, or DNS")
            
            # Update current URL
            current_parsed_url = next_parsed_url
        else:
            break
    
    # Step 3: Return the body text
    return body.decode('utf-8') if isinstance(body, bytes) else str(body)
