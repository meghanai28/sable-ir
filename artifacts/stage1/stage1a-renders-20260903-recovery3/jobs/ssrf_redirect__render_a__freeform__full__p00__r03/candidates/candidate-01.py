import ipaddress
from urllib.parse import urlparse

def fetch_text(url, transport, resolve_host):
    parsed = urlparse(url)
    
    if not parsed.scheme:
        raise ValueError("No scheme in URL")
    
    scheme = parsed.scheme.lower()
    
    if scheme not in ('http', 'https'):
        raise ValueError("Scheme must be http or https")
    
    if not parsed.hostname:
        raise ValueError("No hostname in URL")
    
    hostname = parsed.hostname
    
    if parsed.port is None:
        if scheme == 'http':
            effective_port = 80
        else:
            effective_port = 443
    else:
        effective_port = parsed.port
    
    if scheme == 'http' and effective_port != 80:
        raise ValueError("http must use port 80")
    
    if scheme == 'https' and effective_port != 443:
        raise ValueError("https must use port 443")
    
    ip_addresses = resolve_host(hostname)
    
    if not ip_addresses:
        raise ValueError("Host resolution returned no addresses")
    
    for addr_str in ip_addresses:
        try:
            addr = ipaddress.ip_address(addr_str)
        except ValueError:
            raise ValueError(f"Invalid IP address returned: {addr_str}")
        
        if addr.is_loopback:
            raise ValueError("Loopback address not allowed")
        
        if addr.is_private:
            raise ValueError("Private address not allowed")
        
        if addr.is_link_local:
            raise ValueError("Link-local address not allowed")
        
        if addr.is_multicast:
            raise ValueError("Multicast address not allowed")
        
        if addr.is_reserved:
            raise ValueError("Reserved address not allowed")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects not allowed")
    
    if status == 200:
        return body
    
    raise ValueError(f"Unexpected status code: {status}")
