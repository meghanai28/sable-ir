import socket
import urllib.parse
from typing import Tuple, List

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    # Parse the URL to check scheme and port
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port
    
    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only http and https schemes are allowed")
    
    # Validate port (default ports: http=80, https=443)
    default_port = 80 if scheme == 'http' else 443
    if port != default_port:
        raise ValueError("Only default ports are allowed")
    
    # Resolve hostname to IP addresses
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid URL: missing hostname")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Could not resolve hostname")
    
    # Create the request using the first resolved IP
    # We do not follow redirects; even if the response has a Location header,
    # we must not use it.
    request_url = f"{scheme}://{hostname}"
    if parsed.path:
        request_url += parsed.path
    if parsed.query:
        request_url += f"?{parsed.query}"
    
    # Make the request
    status, headers, body = transport(request_url)
    
    # Check status code
    if status != 200:
        raise ValueError("Only status code 200 is allowed")
    
    return body
