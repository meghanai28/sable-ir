import re
import ipaddress
from urllib.parse import urlparse, urljoin

def fetch_text(url, transport, resolve_host):
    def validate_url(url_to_validate):
        parsed = urlparse(url_to_validate)
        
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
            host_to_resolve = hostname[1:-1]
        else:
            host_to_resolve = hostname
        
        try:
            ip_addr = ipaddress.ip_address(host_to_resolve)
            addresses = [str(ip_addr)]
        except ValueError:
            addresses = resolve_host(host_to_resolve)
            if not addresses:
                raise ValueError("DNS resolution failed")
        
        for addr in addresses:
            ip_obj = ipaddress.ip_address(addr)
            if ip_obj.is_private:
                raise ValueError("Private address")
            if ip_obj.is_loopback:
                raise ValueError("Loopback address")
            if ip_obj.is_reserved:
                raise ValueError("Reserved address")
            if ip_obj.is_multicast:
                raise ValueError("Multicast address")
            if ip_obj.is_link_local:
                raise ValueError("Link-local address")
            if ip_obj.version == 4:
                if ip_obj.is_unspecified:
                    raise ValueError("Unspecified address")
            if ip_obj.version == 6:
                if ip_obj == ipaddress.IPv6Address('::'):
                    raise ValueError("Unspecified address")
        
        return url_to_validate
    
    current_url = validate_url(url)
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
            if isinstance(headers, dict):
                for key, value in headers.items():
                    if key.lower() == 'location':
                        location = value
                        break
            else:
                for key, value in headers:
                    if key.lower() == 'location':
                        location = value
                        break
            
            if location is None:
                raise ValueError("Missing Location header")
            
            current_url = validate_url(urljoin(current_url, location))
            continue
        
        raise ValueError("Unexpected status")
