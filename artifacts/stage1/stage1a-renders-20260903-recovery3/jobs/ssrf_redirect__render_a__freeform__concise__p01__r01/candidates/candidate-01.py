import re
import ipaddress

def fetch_text(url, transport, resolve_host):
    scheme_match = re.match(r'^([a-zA-Z][a-zA-Z0-9+.-]*)://', url)
    if not scheme_match:
        raise ValueError("Invalid URL: missing scheme")
    scheme = scheme_match.group(1).lower()
    
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme: only http and https are allowed")
    
    default_port = 80 if scheme == 'http' else 443
    
    rest = url[scheme_match.end():]
    
    path_start = rest.find('/')
    if path_start == -1:
        authority = rest
        path = ''
    else:
        authority = rest[:path_start]
        path = rest[path_start:]
    
    if '@' in authority:
        raise ValueError("Invalid URL: userinfo not allowed")
    
    if '[' in authority:
        raise ValueError("Invalid URL: IPv6 addresses not supported")
    
    if ':' in authority:
        host, port_str = authority.rsplit(':', 1)
        if not port_str.isdigit():
            raise ValueError("Invalid URL: invalid port")
        port = int(port_str)
    else:
        host = authority
        port = default_port
    
    if not host:
        raise ValueError("Invalid URL: missing host")
    
    if port != default_port:
        raise ValueError("Invalid port: must be default port for scheme")
    
    resolved_ips = resolve_host(host)
    
    for ip_str in resolved_ips:
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError("Invalid IP address from resolver")
        
        if addr.is_private:
            raise ValueError("Non-public IP address")
        if addr.is_loopback:
            raise ValueError("Non-public IP address")
        if addr.is_reserved:
            raise ValueError("Non-public IP address")
        if addr.is_link_local:
            raise ValueError("Non-public IP address")
        if addr.is_multicast:
            raise ValueError("Non-public IP address")
        if addr.is_unspecified:
            raise ValueError("Non-public IP address")
        if getattr(addr, 'is_site_local', False):
            raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects not allowed")
    
    if status != 200:
        raise ValueError("Non-200 status: {}".format(status))
    
    return body
