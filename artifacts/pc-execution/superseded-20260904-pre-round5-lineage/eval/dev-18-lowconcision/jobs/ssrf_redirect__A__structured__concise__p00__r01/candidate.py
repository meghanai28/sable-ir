import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetches text from a URL, resolving the hostname and validating the protocol/port.
    Does not follow redirects.
    """
    # Parse the URL to check scheme and netloc
    parsed = urllib.parse.urlparse(url)
    
    # Guard: Reject absolute URLs that are not http or https
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Guard: Reject if no netloc (absolute URL)
    if not parsed.netloc:
        raise ValueError("Absolute URL with netloc is required")
    
    # Guard: Resolve hostname
    try:
        resolved_ips = resolve_host(parsed.netloc)
        if not resolved_ips:
            raise ValueError("Hostname is not reachable")
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname: {e}")
    
    # Guard: Accept only HTTP or HTTPS on default port
    default_ports = {'http': 80, 'https': 443}
    port = parsed.port
    scheme = parsed.scheme
    
    if port is None:
        port = default_ports[scheme]
    
    if port != default_ports[scheme]:
        raise ValueError(f"Only HTTP on port 80 or HTTPS on port 443 are allowed")
    
    # Construct the request
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Python-urllib')
    
    # Open the connection (no follow_redirects=True by default)
    try:
        response = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        raise ValueError(f"Request failed with status {e.code}")
    except urllib.error.URLError as e:
        raise ValueError(f"Connection failed: {e.reason}")
    
    # Guard: Check status code
    if response.status != 200:
        raise ValueError(f"Expected status 200, got {response.status}")
    
    # Return the body text
    return response.read().decode('utf-8')
