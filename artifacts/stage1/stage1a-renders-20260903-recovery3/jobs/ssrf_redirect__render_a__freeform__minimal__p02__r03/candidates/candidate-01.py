import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    default_port = 80 if parsed.scheme == 'http' else 443
    
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Invalid port")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("No hostname")
    
    ips = resolve_host(hostname)
    if not ips:
        raise ValueError("No IP addresses resolved")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects not allowed")
    
    if status == 200:
        return body
    
    raise ValueError("Unexpected status")
