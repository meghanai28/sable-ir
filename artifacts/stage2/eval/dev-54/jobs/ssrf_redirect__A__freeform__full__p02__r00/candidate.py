import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the URL to extract scheme and host
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname
    
    # Validate scheme: only HTTP or HTTPS on default ports are allowed
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Determine the default port
    default_port = 80 if scheme == 'http' else 443
    
    # Resolve the hostname to IP address(es)
    ip_addresses = resolve_host(host)
    
    # Raise ValueError if no IP addresses are resolved
    if not ip_addresses:
        raise ValueError("No IP address could be resolved for the hostname.")
    
    # Construct the full URL with the default port
    full_url = f"{scheme}://{host}:{default_port}"
    
    # Perform the transport request
    try:
        response = transport(full_url)
    except Exception as e:
        raise ValueError(f"Request failed: {e}")
    
    # Check status code: must be exactly 200
    status, headers, body = response
    if status != 200:
        raise ValueError(f"Status code is not 200: {status}")
    
    # Check if body is None or empty
    if body is None or (isinstance(body, str) and body.strip() == ''):
        raise ValueError("Response body is empty.")
    
    # Return the body
    return body if isinstance(body, str) else body.decode('utf-8')
