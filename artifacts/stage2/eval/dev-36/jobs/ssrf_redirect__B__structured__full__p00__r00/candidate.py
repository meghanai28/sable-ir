import socket
import urllib.parse

def fetch_text(url, transport, resolve_host):
    # Parse the URL to extract scheme, netloc, and path
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme
    netloc = parsed.netloc
    path = parsed.path
    
    # GUARD: Check scheme is http or https
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # GUARD: Resolve hostname to IP address(es)
    hostname = netloc
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("resolve_host did not return any IP addresses")
    
    # Determine port based on scheme
    if scheme == 'http':
        port = 80
    else:
        port = 443
    
    # Construct the full URL with port for transport
    full_url = f"{scheme}://{hostname}:{port}{path}"
    
    # Call transport to get response
    status, headers, body = transport(full_url)
    
    # ORDER: Return body only if status is exactly 200
    if status == 200:
        return body
    else:
        raise ValueError("Request failed: status code is not 200")
