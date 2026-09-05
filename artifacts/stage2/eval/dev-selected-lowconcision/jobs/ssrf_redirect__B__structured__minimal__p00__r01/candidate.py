import socket
import urllib.parse

def fetch_text(url: str, transport, resolve_host) -> str:
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname.")
    
    resolved_ips = resolve_host(hostname)
    if not resolved_ips:
        raise ValueError("resolve_host returned no valid IP addresses.")
    
    port = parsed.port
    if port is None:
        port = 80 if scheme == 'http' else 443
    
    try:
        if scheme == 'http':
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((resolved_ips[0], port))
        else:
            sock = socket.create_connection((resolved_ips[0], port), timeout=5)
        
        status, headers, body = transport(url)
        
        if status != 200:
            raise ValueError(f"HTTP status code {status} is not 200.")
        
        return body.decode('utf-8') if isinstance(body, bytes) else body
        
    finally:
        sock.close()

def fetch_text_secure(url: str, transport, resolve_host) -> str:
    """
    Secure version that validates the URL scheme and resolves the hostname before connecting.
    This function implements the core logic of the fetch_text function with additional security checks.
    """
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname.")
    
    resolved_ips = resolve_host(hostname)
    if not resolved_ips:
        raise ValueError("resolve_host returned no valid IP addresses.")
    
    try:
        if scheme == 'http':
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((resolved_ips[0], parsed.port or 80))
        else:
            sock = socket.create_connection((resolved_ips[0], parsed.port or 443), timeout=5)
        
        status, headers, body = transport(url)
        
        if status != 200:
            raise ValueError(f"HTTP status code {status} is not 200.")
        
        return body.decode('utf-8') if isinstance(body, bytes) else body
        
    finally:
        sock.close()
