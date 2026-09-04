import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme
    hostname = parsed.hostname
    port = parsed.port
    
    if not scheme or not hostname:
        raise ValueError("Invalid URL")
    
    if scheme == "http":
        if port is None:
            port = 80
        if port != 80:
            raise ValueError("Non-default port for http")
    elif scheme == "https":
        if port is None:
            port = 443
        if port != 443:
            raise ValueError("Non-default port for https")
    else:
        raise ValueError("Invalid scheme")
    
    ip_addresses = resolve_host(hostname)
    
    if not ip_addresses:
        raise ValueError("No IP addresses resolved")
    
    for addr_str in ip_addresses:
        try:
            addr = ipaddress.ip_address(addr_str)
        except ValueError:
            raise ValueError("Invalid IP address")
        
        if addr.is_loopback:
            raise ValueError("Loopback address")
        if addr.is_private:
            raise ValueError("Private address")
        if addr.is_link_local:
            raise ValueError("Link-local address")
        if addr.is_multicast:
            raise ValueError("Multicast address")
        if addr.is_reserved:
            raise ValueError("Reserved address")
        if addr.is_unspecified:
            raise ValueError("Unspecified address")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status == 200:
        return body
    
    raise ValueError("Non-200 status code")
