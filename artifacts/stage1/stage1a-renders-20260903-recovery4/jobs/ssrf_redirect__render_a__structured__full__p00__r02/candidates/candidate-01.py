import ipaddress
import re
from urllib.parse import urlparse

def fetch_text(url, transport, resolve_host):
    parsed = urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    default_port = 80 if scheme == 'http' else 443
    
    host = parsed.hostname
    if host is None or host == '':
        raise ValueError("Empty host")
    
    port = parsed.port
    if port is not None and port != default_port:
        raise ValueError("Non-default port")
    
    def is_public_ip(addr_str):
        try:
            addr = ipaddress.ip_address(addr_str)
        except ValueError:
            return False
        
        if addr.version == 4:
            if addr.is_loopback:
                return False
            if addr.is_private:
                return False
            if addr.is_link_local:
                return False
            if addr.is_multicast:
                return False
            if addr.is_reserved:
                return False
            if addr.is_unspecified:
                return False
            return True
        else:
            if addr.is_loopback:
                return False
            if addr.is_link_local:
                return False
            if addr.is_multicast:
                return False
            if addr.is_unspecified:
                return False
            
            int_addr = int(addr)
            fc00 = int(ipaddress.IPv6Address('fc00::'))
            fdff = int(ipaddress.IPv6Address('fdff:ffff:ffff:ffff:ffff:ffff:ffff:ffff'))
            if fc00 <= int_addr <= fdff:
                return False
            
            return True
    
    def is_literal_ip(host_str):
        try:
            ipaddress.ip_address(host_str)
            return True
        except ValueError:
            return False
    
    if is_literal_ip(host):
        addresses = [host]
    else:
        addresses = resolve_host(host)
        if not addresses:
            raise ValueError("DNS resolution failed")
    
    for addr in addresses:
        if not is_public_ip(addr):
            raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not followed")
    
    if status != 200:
        raise ValueError("Non-200 status code")
    
    return body
