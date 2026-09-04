import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    if parsed.scheme == 'http':
        allowed_port = 80
    else:
        allowed_port = 443
    
    if parsed.port is not None and parsed.port != allowed_port:
        raise ValueError("Disallowed port")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")
    
    resolved_ips = resolve_host(hostname)
    
    for ip_text in resolved_ips:
        addr = ipaddress.ip_address(ip_text)
        if addr.is_loopback:
            raise ValueError("Loopback address")
        if addr.is_private:
            raise ValueError("Private address")
        if addr.is_link_local:
            raise ValueError("Link-local address")
        if addr.is_multicast:
            raise ValueError("Multicast address")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    return body
