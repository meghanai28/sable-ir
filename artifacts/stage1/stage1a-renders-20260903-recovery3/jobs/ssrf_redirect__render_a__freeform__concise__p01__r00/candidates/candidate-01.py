import re
import ipaddress

def fetch_text(url, transport, resolve_host):
    scheme, host, port = _parse_url(url)
    
    if scheme not in ('http', 'https'):
        raise ValueError("Scheme must be http or https")
    
    default_port = 80 if scheme == 'http' else 443
    if port != default_port:
        raise ValueError("Port must be the default for the scheme")
    
    ip_addresses = resolve_host(host)
    for ip_str in ip_addresses:
        addr = ipaddress.ip_address(ip_str)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_reserved or addr.is_unspecified:
            raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects are not followed")
    
    if status != 200:
        raise ValueError(f"Unexpected status: {status}")
    
    return body

def _parse_url(url):
    pattern = r'^(https?)://([^/:]+)(?::(\d+))?(?:/.*)?$'
    match = re.match(pattern, url)
    if not match:
        raise ValueError("Invalid URL")
    
    scheme = match.group(1)
    host = match.group(2)
    port_str = match.group(3)
    
    if port_str is not None:
        port = int(port_str)
    else:
        port = 80 if scheme == 'http' else 443
    
    return scheme, host, port
