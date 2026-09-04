import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    def validate_url(target_url):
        parsed = urllib.parse.urlparse(target_url)
        
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        if parsed.scheme == 'http':
            allowed_ports = (80, None)
        else:
            allowed_ports = (443, None)
        
        port = parsed.port
        if port is not None and port not in allowed_ports:
            raise ValueError("Non-default port")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")
        
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        if hostname.startswith('[') and hostname.endswith(']'):
            host_for_resolve = hostname[1:-1]
        else:
            host_for_resolve = hostname
        
        try:
            ipaddress.ip_address(host_for_resolve)
            is_literal_ip = True
        except ValueError:
            is_literal_ip = False
        
        if is_literal_ip:
            ip_addrs = [host_for_resolve]
        else:
            ip_addrs = resolve_host(host_for_resolve)
        
        if not ip_addrs:
            raise ValueError("DNS resolution failed")
        
        for addr in ip_addrs:
            try:
                ip_obj = ipaddress.ip_address(addr)
            except ValueError:
                raise ValueError("Invalid IP address")
            
            if ip_obj.is_private:
                raise ValueError("Private IP address")
            if ip_obj.is_loopback:
                raise ValueError("Loopback IP address")
            if ip_obj.is_reserved:
                raise ValueError("Reserved IP address")
            if ip_obj.is_multicast:
                raise ValueError("Multicast IP address")
            if ip_obj.is_link_local:
                raise ValueError("Link-local IP address")
            if ip_obj.version == 4 and ip_obj.is_unspecified:
                raise ValueError("Unspecified IP address")
            if ip_obj.version == 6 and ip_obj.is_unspecified:
                raise ValueError("Unspecified IP address")
            if hasattr(ip_obj, 'is_site_local') and ip_obj.is_site_local:
                raise ValueError("Site-local IP address")
        
        return parsed
    
    current_url = url
    validate_url(current_url)
    
    hop_count = 0
    
    while True:
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 307, 308):
            hop_count += 1
            if hop_count > 5:
                raise ValueError("Too many redirects")
            
            location = None
            for key, value in headers.items() if isinstance(headers, dict) else headers:
                if key.lower() == 'location':
                    location = value
                    break
            
            if location is None:
                raise ValueError("Missing Location header")
            
            current_url = urllib.parse.urljoin(current_url, location)
            validate_url(current_url)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
