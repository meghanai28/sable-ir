import ipaddress
import re

def fetch_text(url, transport, resolve_host):
    scheme, hostname, port = _parse_url(url)
    
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    if scheme == 'http' and port is not None and port != 80:
        raise ValueError("Invalid port for http")
    if scheme == 'https' and port is not None and port != 443:
        raise ValueError("Invalid port for https")
    
    addresses = resolve_host(hostname)
    if not addresses:
        raise ValueError("No addresses resolved")
    
    for addr in addresses:
        if not _is_public_address(addr):
            raise ValueError("Non-public address resolved")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    return body

def _parse_url(url):
    url_pattern = re.compile(
        r'^(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*)://'
        r'(?P<host>[^:/\[\]?#]+|\[[^\]]+\])'
        r'(?::(?P<port>\d+))?'
        r'(?:/|$)'
    )
    
    match = url_pattern.match(url)
    if not match:
        raise ValueError("Invalid URL")
    
    scheme = match.group('scheme').lower()
    host = match.group('host')
    port_str = match.group('port')
    
    port = int(port_str) if port_str is not None else None
    
    if host.startswith('[') and host.endswith(']'):
        hostname = host[1:-1]
    else:
        hostname = host
    
    return scheme, hostname, port

def _is_public_address(addr):
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    
    if isinstance(ip, ipaddress.IPv4Address):
        if ip.is_private:
            return False
        if ip.is_loopback:
            return False
        if ip.is_link_local:
            return False
        if ip.is_multicast:
            return False
        if ip.is_reserved:
            return False
        if ip.is_unspecified:
            return False
        if ip == ipaddress.IPv4Address('255.255.255.255'):
            return False
    elif isinstance(ip, ipaddress.IPv6Address):
        if ip.is_private:
            return False
        if ip.is_loopback:
            return False
        if ip.is_link_local:
            return False
        if ip.is_multicast:
            return False
        if ip.is_reserved:
            return False
        if ip.is_unspecified:
            return False
        if ip.ipv4_mapped is not None:
            if not _is_public_address(str(ip.ipv4_mapped)):
                return False
    
    return True
