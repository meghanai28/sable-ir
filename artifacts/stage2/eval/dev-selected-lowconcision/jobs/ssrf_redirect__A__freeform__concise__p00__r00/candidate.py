import socket
import urllib.parse
import urllib.request
from urllib.error import URLError

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Validate scheme
    if parsed_url.scheme.lower() not in ['http', 'https']:
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Determine the default port
    default_port = 80 if parsed_url.scheme.lower() == 'http' else 443
    
    # Resolve hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("URL must have a hostname")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Failed to resolve hostname")
    
    if not ip_addresses:
        raise ValueError("No IP addresses found for hostname")
    
    # Build the full URL with default port if not specified
    full_url = parsed_url._replace(port=default_port).geturl()
    
    # Use urllib to handle the request
    try:
        response = urllib.request.urlopen(full_url)
    except Exception as e:
        raise ValueError(f"Request failed: {e}")
    
    status_code = response.status
    
    # Check status code
    if status_code != 200:
        raise ValueError(f"Unexpected status code: {status_code}")
    
    # Read and return the body
    body = response.read().decode('utf-8')
    return body
