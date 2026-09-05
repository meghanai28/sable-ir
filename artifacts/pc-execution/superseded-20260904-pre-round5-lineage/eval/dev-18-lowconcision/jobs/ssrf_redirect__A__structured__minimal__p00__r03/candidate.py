import socket
import urllib.parse
import urllib.request

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    if url.startswith(('http://', 'https://')):
        raise ValueError("Absolute URLs are not allowed")
    
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid URL")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Host {hostname} is not reachable")
    
    if not ip_addresses:
        raise ValueError(f"Host {hostname} is not reachable")
    
    request = urllib.request.Request(url)
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as e:
        if e.code != 200:
            raise ValueError(f"Disallowed request: HTTP {e.code}")
        return e.read().decode('utf-8')
    except urllib.error.URLError as e:
        raise ValueError(f"Connection failed: {e}")
    
    return response.read().decode('utf-8')
