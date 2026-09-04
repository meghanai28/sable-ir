import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    max_hops = 5
    hop_count = 0
    
    current_url = url
    
    while True:
        if hop_count > max_hops:
            raise ValueError("Too many redirects")
        
        parsed = urllib.parse.urlparse(current_url)
        
        # Validate scheme
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        # Validate port (must be default or not specified)
        if parsed.scheme == 'http':
            default_port = 80
        else:
            default_port = 443
        
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Non-default port not allowed")
        
        # Validate no credentials
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")
        
        # Validate hostname exists
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        # Resolve hostname and validate
        ip_texts = resolve_host(hostname)
        if not ip_texts:
            raise ValueError("Hostname resolution failed")
        
        for ip_text in ip_texts:
            try:
                ip = ipaddress.ip_address(ip_text)
            except ValueError:
                raise ValueError("Invalid IP address from resolver")
            
            # Check for private/reserved/loopback addresses
            if ip.is_private:
                raise ValueError("Private IP address not allowed")
            if ip.is_loopback:
                raise ValueError("Loopback IP address not allowed")
            if ip.is_reserved:
                raise ValueError("Reserved IP address not allowed")
            if ip.is_multicast:
                raise ValueError("Multicast IP address not allowed")
            if ip.is_link_local:
                raise ValueError("Link-local IP address not allowed")
            if hasattr(ip, 'is_global') and not ip.is_global:
                # is_global available in Python 3.4+, covers some cases
                pass
        
        # Reconstruct URL with normalized port (no port for default)
        netloc = hostname
        if parsed.port is not None and parsed.port != default_port:
            netloc = f"{hostname}:{parsed.port}"
        
        normalized_url = urllib.parse.urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        
        # Make transport call
        status, headers, body = transport(normalized_url)
        
        if status == 200:
            return body
        
        # Handle redirects
        if 300 <= status < 400:
            hop_count += 1
            if hop_count > max_hops:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect without Location header")
            
            # Resolve Location against current URL
            current_url = urllib.parse.urljoin(current_url, location)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
