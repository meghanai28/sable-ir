import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if parsed.port is None:
        if scheme == 'http':
            port = 80
        else:
            port = 443
    else:
        port = parsed.port
    
    if scheme == 'http' and port != 80:
        raise ValueError("HTTP must use port 80")
    if scheme == 'https' and port != 443:
        raise ValueError("HTTPS must use port 443")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("URL must have a hostname")
    
    ip_addresses = resolve_host(hostname)
    
    for ip_str in ip_addresses:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_loopback:
            raise ValueError("Loopback address not allowed")
        if ip.is_private:
            raise ValueError("Private address not allowed")
        if ip.is_link_local:
            raise ValueError("Link-local address not allowed")
        if ip.is_multicast:
            raise ValueError("Multicast address not allowed")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects are not allowed")
    
    if status != 200:
        raise ValueError(f"Unexpected status: {status}")
    
    return body
