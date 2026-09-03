import urllib.parse

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    redirect_count = 0
    
    current_url = url
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        
        # Validate scheme
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Only HTTP and HTTPS schemes are allowed")
        
        # Validate port (must be default or not specified)
        default_port = 443 if parsed.scheme == 'https' else 80
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Non-default port not allowed")
        
        # Validate hostname exists
        if not parsed.hostname:
            raise ValueError("URL must have a hostname")
        
        # DNS and public-address validation via resolve_host
        try:
            ip_addresses = resolve_host(parsed.hostname)
        except Exception:
            raise ValueError("DNS resolution failed")
        
        if not ip_addresses:
            raise ValueError("DNS resolution returned no addresses")
        
        # Check credentials: reject if userinfo present in URL
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials in URL are not allowed")
        
        # Make the request using transport
        status, headers, body = transport(current_url)
        
        # Handle redirect
        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            # Find Location header
            location = None
            for name, value in headers:
                if name.lower() == 'location':
                    location = value
                    break
            
            if location is None:
                raise ValueError("Redirect response missing Location header")
            
            # Resolve Location against current URL
            new_url = urllib.parse.urljoin(current_url, location)
            new_parsed = urllib.parse.urlparse(new_url)
            
            # Validate scheme, port, credential, DNS, and public-address same as initial destination
            
            # Scheme validation
            if new_parsed.scheme not in ('http', 'https'):
                raise ValueError("Redirect scheme not allowed")
            
            # Port validation
            new_default_port = 443 if new_parsed.scheme == 'https' else 80
            if new_parsed.port is not None and new_parsed.port != new_default_port:
                raise ValueError("Redirect to non-default port not allowed")
            
            # Credential validation
            if new_parsed.username is not None or new_parsed.password is not None:
                raise ValueError("Redirect with credentials not allowed")
            
            # DNS validation
            if not new_parsed.hostname:
                raise ValueError("Redirect URL must have a hostname")
            
            try:
                new_ip_addresses = resolve_host(new_parsed.hostname)
            except Exception:
                raise ValueError("Redirect DNS resolution failed")
            
            if not new_ip_addresses:
                raise ValueError("Redirect DNS resolution returned no addresses")
            
            current_url = new_url
            continue
        
        # Return body for 200 OK
        if status == 200:
            return body
        
        # Other status codes are errors
        raise ValueError(f"Unexpected status code: {status}")
