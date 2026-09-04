import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme == 'http':
        default_port = 80
    elif scheme == 'https':
        default_port = 443
    else:
        raise ValueError("Disallowed scheme")
    
    if ':' in parsed.netloc:
        host_part, port_part = parsed.netloc.rsplit(':', 1)
        try:
            port = int(port_part)
        except ValueError:
            host_part = parsed.netloc
            port = default_port
    else:
        host_part = parsed.netloc
        port = default_port
    
    if port != default_port:
        raise ValueError("Non-default port")
    
    hostname = host_part
    if hostname.startswith('[') and hostname.endswith(']'):
        hostname = hostname[1:-1]
    
    try:
        ip_addrs = resolve_host(hostname)
    except Exception:
        raise ValueError("Resolution failed")
    
    if not ip_addrs:
        raise ValueError("Resolution failed")
    
    for addr in ip_addrs:
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            raise ValueError("Invalid IP address")
        
        if ip.is_private:
            raise ValueError("Non-public IP address")
        if ip.is_loopback:
            raise ValueError("Non-public IP address")
        if ip.is_reserved:
            raise ValueError("Non-public IP address")
        if ip.is_multicast:
            raise ValueError("Non-public IP address")
        if ip.is_link_local:
            raise ValueError("Non-public IP address")
        if ip.is_unspecified:
            raise ValueError("Non-public IP address")
        if hasattr(ip, 'is_site_local') and ip.is_site_local:
            raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not followed")
    
    if status == 200:
        return body
    
    raise ValueError("Unexpected status")
