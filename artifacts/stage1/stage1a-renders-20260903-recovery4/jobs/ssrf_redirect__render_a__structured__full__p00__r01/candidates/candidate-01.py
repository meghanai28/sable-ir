import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
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
            if addr.is_reserved:
                return False
            if addr.is_multicast:
                return False
            if addr.is_unspecified:
                return False
            return True
        
        if addr.version == 6:
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
        
        return False
    
    try:
        test_addr = ipaddress.ip_address(host)
        is_literal_ip = True
    except ValueError:
        is_literal_ip = False
    
    if is_literal_ip:
        addresses = [host]
    else:
        addresses = resolve_host(host)
        if not addresses:
            raise ValueError("Host resolution failed")
    
    for addr_str in addresses:
        if not is_public_ip(addr_str):
            raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError("Non-200 status code")
    
    return body
