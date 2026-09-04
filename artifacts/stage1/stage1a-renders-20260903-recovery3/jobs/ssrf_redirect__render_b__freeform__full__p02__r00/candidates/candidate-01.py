import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    max_redirects = 5
    redirect_count = 0
    
    def validate_url(url_str):
        parsed = urllib.parse.urlparse(url_str)
        
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Disallowed scheme")
        
        default_port = 80 if scheme == 'http' else 443
        
        host = parsed.hostname
        if host is None:
            raise ValueError("Missing hostname")
        
        port = parsed.port
        if port is not None and port != default_port:
            raise ValueError("Non-default port")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Embedded credentials not allowed")
        
        netloc = host
        if port is not None:
            netloc = f"{host}:{port}"
        else:
            netloc = host
        
        path = parsed.path if parsed.path else '/'
        query = f"?{parsed.query}" if parsed.query else ""
        fragment = ""
        
        reconstructed = urllib.parse.urlunparse((
            scheme, netloc, path, parsed.params, parsed.query, fragment
        ))
        
        return reconstructed, host
    
    def validate_host(hostname):
        try:
            ips = resolve_host(hostname)
        except Exception:
            raise ValueError("Host resolution failed")
        
        if not ips:
            raise ValueError("No IP addresses returned")
        
        for ip_str in ips:
            try:
                addr = ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError("Invalid IP address format")
            
            if addr.version == 4:
                if addr.is_private:
                    raise ValueError("Private IPv4 address")
                if addr.is_loopback:
                    raise ValueError("Loopback IPv4 address")
                if addr.is_reserved:
                    raise ValueError("Reserved IPv4 address")
                if addr.is_multicast:
                    raise ValueError("Multicast IPv4 address")
                if addr.is_link_local:
                    raise ValueError("Link-local IPv4 address")
                if addr.is_unspecified:
                    raise ValueError("Unspecified IPv4 address")
            elif addr.version == 6:
                if addr.is_private:
                    raise ValueError("Private IPv6 address")
                if addr.is_loopback:
                    raise ValueError("Loopback IPv6 address")
                if addr.is_reserved:
                    raise ValueError("Reserved IPv6 address")
                if addr.is_multicast:
                    raise ValueError("Multicast IPv6 address")
                if addr.is_link_local:
                    raise ValueError("Link-local IPv6 address")
                if addr.is_unspecified:
                    raise ValueError("Unspecified IPv6 address")
    
    def resolve_location(base_url, location):
        if not location:
            raise ValueError("Missing Location header")
        absolute = urllib.parse.urljoin(base_url, location)
        return absolute
    
    current_url = url
    
    while True:
        validated_url, hostname = validate_url(current_url)
        validate_host(hostname)
        
        try:
            status, headers, body = transport(validated_url)
        except Exception:
            raise ValueError("Transport failed")
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location') if isinstance(headers, dict) else None
            if location is None:
                if isinstance(headers, (list, tuple)):
                    for name, value in headers:
                        if name.lower() == 'location':
                            location = value
                            break
            
            if not location:
                raise ValueError("Missing Location header")
            
            current_url = resolve_location(validated_url, location)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
