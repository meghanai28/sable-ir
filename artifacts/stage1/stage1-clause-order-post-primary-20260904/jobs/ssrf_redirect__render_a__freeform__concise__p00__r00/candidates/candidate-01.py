import ipaddress
import re

def fetch_text(url, transport, resolve_host):
    parsed = _parse_url(url)
    scheme = parsed['scheme']
    host = parsed['host']
    port = parsed['port']
    
    if scheme not in ('http', 'https'):
        raise ValueError("Only http and https schemes are allowed")
    
    if scheme == 'http' and port != 80:
        raise ValueError("http must use port 80")
    if scheme == 'https' and port != 443:
        raise ValueError("https must use port 443")
    
    if not host:
        raise ValueError("Host is required")
    
    ip_addresses = resolve_host(host)
    for ip_str in ip_addresses:
        addr = ipaddress.ip_address(ip_str)
        if not _is_public_routable(addr):
            raise ValueError("Host resolves to non-public IP address")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects are not followed")
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body

def _parse_url(url):
    scheme = None
    host = None
    port = None
    
    if '://' in url:
        scheme_part, rest = url.split('://', 1)
        scheme = scheme_part.lower()
    else:
        rest = url
    
    path_start = rest.find('/')
    if path_start == -1:
        authority = rest
        rest = ''
    else:
        authority = rest[:path_start]
        rest = rest[path_start:]
    
    if '@' in authority:
        userinfo, authority = authority.rsplit('@', 1)
    
    if authority.startswith('['):
        bracket_end = authority.find(']')
        if bracket_end == -1:
            raise ValueError("Invalid IPv6 literal")
        host = authority[1:bracket_end]
        port_part = authority[bracket_end + 1:]
        if port_part.startswith(':'):
            port = int(port_part[1:])
        else:
            port = None
    elif ':' in authority:
        host, port_str = authority.rsplit(':', 1)
        if host == '':
            raise ValueError("Missing host")
        try:
            port = int(port_str)
        except ValueError:
            host = authority
            port = None
    else:
        host = authority
        port = None
    
    if port is None:
        if scheme == 'http':
            port = 80
        elif scheme == 'https':
            port = 443
    
    return {
        'scheme': scheme,
        'host': host,
        'port': port,
    }

def _is_public_routable(addr):
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
    if addr.version == 4:
        if addr == ipaddress.ip_address('0.0.0.0'):
            return False
        if addr == ipaddress.ip_address('255.255.255.255'):
            return False
        first_octet = int(str(addr).split('.')[0])
        if first_octet == 0 or first_octet == 127 or first_octet >= 224:
            return False
    if addr.version == 6:
        if addr == ipaddress.ip_address('::'):
            return False
        if addr == ipaddress.ip_address('::1'):
            return False
        if str(addr).lower().startswith('fe80:'):
            return False
        if str(addr).lower().startswith('fc') or str(addr).lower().startswith('fd'):
            return False
        if str(addr).lower().startswith('ff'):
            return False
    
    return True
