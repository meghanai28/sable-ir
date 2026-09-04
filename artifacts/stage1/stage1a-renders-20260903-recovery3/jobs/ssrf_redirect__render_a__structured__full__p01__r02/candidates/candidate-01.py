import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    default_port = 80 if scheme == 'http' else 443
    
    host = parsed.hostname
    port = parsed.port
    
    if host is None or host == '':
        raise ValueError("Empty host")
    
    if port is None:
        port = default_port
    
    if port != default_port:
        raise ValueError("Non-default port")
    
    ips = resolve_host(host)
    
    for ip_str in ips:
        ip = ipaddress.ip_address(ip_str)
        
        if ip.is_loopback:
            raise ValueError("Non-public IP")
        if ip.is_link_local:
            raise ValueError("Non-public IP")
        if ip.is_private:
            raise ValueError("Non-public IP")
        if ip.is_reserved:
            raise ValueError("Non-public IP")
        if ip.is_multicast:
            raise ValueError("Non-public IP")
        if hasattr(ip, 'is_global') and not ip.is_global:
            raise ValueError("Non-public IP")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    return body
