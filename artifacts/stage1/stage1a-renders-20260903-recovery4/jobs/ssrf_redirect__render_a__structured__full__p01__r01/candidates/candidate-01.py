import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError("Invalid scheme")
    
    hostname = parsed.hostname
    if hostname is None or hostname == "":
        raise ValueError("Empty host")
    
    if scheme == "http":
        default_port = 80
    else:
        default_port = 443
    
    port = parsed.port
    if port is None:
        port = default_port
    
    if port != default_port:
        raise ValueError("Non-default port")
    
    ip_texts = resolve_host(hostname)
    
    for ip_text in ip_texts:
        ip = ipaddress.ip_address(ip_text)
        
        if ip.is_loopback:
            raise ValueError("Non-public IP")
        if ip.is_link_local:
            raise ValueError("Non-public IP")
        if ip.is_private:
            raise ValueError("Non-public IP")
        if ip.is_reserved:
            raise ValueError("Non-public IP")
        if ip.is_multicast:
            raise ValueError("Non-public IP")
        if hasattr(ip, 'is_documentation') and ip.is_documentation:
            raise ValueError("Non-public IP")
        if ip_text == "0.0.0.0":
            raise ValueError("Non-public IP")
        if ip_text == "::":
            raise ValueError("Non-public IP")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    return body
