import socket
from urllib.parse import urlparse

def fetch_text(url: str, transport, resolve_host) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    resolved_ips = resolve_host(hostname)
    if not resolved_ips:
        raise ValueError("Resolve host failed for: {}".format(hostname))
    
    port = parsed.port
    if port is None:
        port = 80 if scheme == 'http' else 443
    
    try:
        status, headers, body = transport(url)
    except Exception:
        raise ValueError("Transport failed")
    
    if status != 200:
        raise ValueError("Unexpected status code: {}".format(status))
    
    return body
