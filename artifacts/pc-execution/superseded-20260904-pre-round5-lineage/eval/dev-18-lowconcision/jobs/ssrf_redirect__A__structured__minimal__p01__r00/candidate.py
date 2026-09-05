import socket
import urllib.parse
import urllib.request

def fetch_text(url: str, transport, resolve_host) -> str:
    if url.startswith('http://') or url.startswith('https://'):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Only HTTP and HTTPS are allowed")
        if parsed.netloc == '':
            raise ValueError("Absolute URL required")
        hostname = parsed.netloc
        if '..' in hostname:
            raise ValueError("Relative path segments not allowed in hostname")
        
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError("Hostname not reachable")
        
        scheme = parsed.scheme
        port = parsed.port
        if port is None:
            if scheme == 'http':
                port = 80
            elif scheme == 'https':
                port = 443
        path = parsed.path
        if parsed.query:
            path += '?' + parsed.query
        
        if port is None:
            port = 80 if scheme == 'http' else 443
        
        full_url = f"{scheme}://{hostname}:{port}{path}"
        
        req = urllib.request.Request(full_url, method='GET')
        try:
            response = transport(url)
        except Exception as e:
            raise ValueError(f"Request failed: {e}")
        
        status, headers, body = response
        
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        if 'Location' in headers:
            raise ValueError("Redirects are not allowed")
        
        return body.decode('utf-8') if isinstance(body, bytes) else body

def fetch_text_secure(url: str, transport, resolve_host) -> str:
    if not url.startswith(('http://', 'https://')):
        raise ValueError("Only HTTP and HTTPS are allowed")
    
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.netloc
    
    if '..' in hostname:
        raise ValueError("Relative path segments not allowed in hostname")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Hostname not reachable")
    
    scheme = parsed.scheme
    port = parsed.port
    if port is None:
        port = 80 if scheme == 'http' else 443
    
    full_url = f"{scheme}://{hostname}:{port}{parsed.path}"
    
    req = urllib.request.Request(full_url, method='GET')
    try:
        response = transport(url)
    except Exception as e:
        raise ValueError(f"Request failed: {e}")
    
    status, headers, body = response
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    if 'Location' in headers:
        raise ValueError("Redirects are not allowed")
    
    return body.decode('utf-8') if isinstance(body, bytes) else body
