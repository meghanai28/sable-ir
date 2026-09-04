import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    host = parsed.hostname
    if host is None or host == '':
        raise ValueError("Empty host")
    
    default_port = 80 if scheme == 'http' else 443
    
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Non-default port")
    
    addresses = []
    try:
        addr = ipaddress.ip_address(host)
        addresses.append(str(addr))
    except ValueError:
        resolved = resolve_host(host)
        if not resolved:
            raise ValueError("Host resolution failed")
        addresses = resolved
    
    for addr_str in addresses:
        addr = ipaddress.ip_address(addr_str)
        
        if addr.version == 4:
            if addr.is_loopback:
                raise ValueError("Non-public IP")
            if addr.is_private:
                raise ValueError("Non-public IP")
            if addr.is_link_local:
                raise ValueError("Non-public IP")
            if addr.is_reserved:
                raise ValueError("Non-public IP")
            if addr.is_multicast:
                raise ValueError("Non-public IP")
            if addr.is_unspecified:
                raise ValueError("Non-public IP")
        elif addr.version == 6:
            if addr.is_loopback:
                raise ValueError("Non-public IP")
            if addr.is_link_local:
                raise ValueError("Non-public IP")
            if addr.is_private:
                raise ValueError("Non-public IP")
            if addr.is_multicast:
                raise ValueError("Non-public IP")
            if addr.is_unspecified:
                raise ValueError("Non-public IP")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    return body
