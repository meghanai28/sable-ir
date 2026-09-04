import re
import ipaddress

def fetch_text(url, transport, resolve_host):
    parsed = _parse_url(url)
    scheme = parsed['scheme']
    host = parsed['host']
    port = parsed['port']
    
    if scheme not in ('http', 'https'):
        raise ValueError("Scheme must be http or https")
    
    default_port = 80 if scheme == 'http' else 443
    if port != default_port:
        raise ValueError("Port must be the default for the scheme")
    
    ip_addresses = resolve_host(host)
    for ip_text in ip_addresses:
        addr = ipaddress.ip_address(ip_text)
        if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_multicast or addr.is_link_local:
            raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects are not followed")
    
    if status != 200:
        raise ValueError("Status must be 200")
    
    return body

def _parse_url(url):
    pattern = r'^(?P<scheme>https?)://(?P<host>[^:/\?#]+)(?::(?P<port>\d+))?(?P<path>/[^\?#]*)?(?:\?[^\#]*)?(?:\#.*)?$'
    match = re.match(pattern, url)
    if not match:
        raise ValueError("Invalid URL")
    
    scheme = match.group('scheme')
    host = match.group('host')
    port_str = match.group('port')
    
    if port_str is None:
        port = 80 if scheme == 'http' else 443
    else:
        port = int(port_str)
    
    return {
        'scheme': scheme,
        'host': host,
        'port': port,
    }
