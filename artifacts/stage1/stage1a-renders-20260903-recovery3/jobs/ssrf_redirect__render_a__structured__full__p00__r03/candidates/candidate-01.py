import ipaddress
import re
from urllib.parse import urlparse

def fetch_text(url, transport, resolve_host):
    parsed = urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    host = parsed.hostname
    if host is None or host == '':
        raise ValueError("Empty host")
    
    default_port = 80 if scheme == 'http' else 443
    
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Non-default port")
    
    host_str = host
    
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
            if addr.is_reserved:
                return False
            if addr.is_multicast:
                return False
            if addr.is_unspecified:
                return False
        elif addr.version == 6:
            if addr.is_loopback:
                return False
            if addr.is_link_local:
                return False
            if addr.is_private:
                return False
            if addr.is_multicast:
                return False
            if addr.is_unspecified:
                return False
            if addr.ipv4_mapped is not None:
                mapped = addr.ipv4_mapped
                if mapped.is_loopback or mapped.is_private or mapped.is_link_local or mapped.is_reserved or mapped.is_multicast or mapped.is_unspecified:
                    return False
        
        return True
    
    def is_literal_ip(s):
        try:
            ipaddress.ip_address(s)
            return True
        except ValueError:
            return False
    
    if is_literal_ip(host_str):
        if not is_public_ip(host_str):
            raise ValueError("Non-public IP")
    else:
        resolved = resolve_host(host_str)
        if not resolved:
            raise ValueError("DNS resolution failed")
        for addr in resolved:
            if not is_public_ip(addr):
                raise ValueError("Non-public resolved IP")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not followed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    return body
