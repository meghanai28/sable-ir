import urllib.parse

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    current_url = url
    hops = 0
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        
        # Validate scheme
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Only HTTP and HTTPS schemes are allowed")
        
        # Validate default port
        if parsed.scheme == 'http':
            default_port = 80
        else:
            default_port = 443
        
        port = parsed.port
        if port is None:
            port = default_port
        
        if port != default_port:
            raise ValueError("Only default ports are allowed")
        
        # Validate no credentials in URL
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials in URLs are not allowed")
        
        # DNS and public-address validation
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("URL must have a hostname")
        
        resolved_ips = resolve_host(hostname)
        if not resolved_ips:
            raise ValueError("Hostname resolution failed")
        
        # Make the request
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        # Handle redirects
        if status in (301, 302, 303, 307, 308):
            hops += 1
            if hops > MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect response missing Location header")
            
            # Resolve Location against current URL
            current_url = urllib.parse.urljoin(current_url, location)
            parsed_redirect = urllib.parse.urlparse(current_url)
            
            # Validate redirect scheme
            if parsed_redirect.scheme not in ('http', 'https'):
                raise ValueError("Redirect scheme must be HTTP or HTTPS")
            
            # Validate redirect uses default port
            if parsed_redirect.scheme == 'http':
                redirect_default_port = 80
            else:
                redirect_default_port = 443
            
            redirect_port = parsed_redirect.port
            if redirect_port is None:
                redirect_port = redirect_default_port
            
            if redirect_port != redirect_default_port:
                raise ValueError("Redirect must use default port")
            
            # Validate no credentials in redirect URL
            if parsed_redirect.username is not None or parsed_redirect.password is not None:
                raise ValueError("Credentials in redirect URLs are not allowed")
            
            # Validate redirect has hostname
            redirect_hostname = parsed_redirect.hostname
            if redirect_hostname is None:
                raise ValueError("Redirect URL must have a hostname")
            
            # DNS and public-address validation for redirect
            redirect_ips = resolve_host(redirect_hostname)
            if not redirect_ips:
                raise ValueError("Redirect hostname resolution failed")
            
            continue
        
        raise ValueError(f"Unexpected status code: {status}")
