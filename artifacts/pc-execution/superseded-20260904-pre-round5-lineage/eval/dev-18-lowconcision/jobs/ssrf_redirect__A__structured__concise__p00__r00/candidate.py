import socket
import urllib.parse

def fetch_text(url: str, transport, resolve_host) -> str:
    # Reject absolute URLs
    if url.startswith(('http://', 'https://')):
        raise ValueError("Absolute URLs are not allowed")
    
    # Parse the URL to extract components
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme and port
    scheme = parsed.scheme.lower()
    port = parsed.port
    
    # Accept only HTTP or HTTPS on default ports
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if scheme == 'http':
        default_port = 80
    elif scheme == 'https':
        default_port = 443
    else:
        raise ValueError("Invalid scheme")
    
    if port is None:
        port = default_port
    elif port != default_port:
        raise ValueError(f"Only default ports are allowed for {scheme}")
    
    # Resolve the hostname
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid URL")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Hostname resolution failed")
    
    if not ip_addresses:
        raise ValueError("No reachable IP addresses found")
    
    # Use the first resolved IP address
    resolved_hostname = ip_addresses[0]
    
    # Construct the full URL with the resolved IP
    full_url = f"{scheme}://{resolved_hostname}{parsed.path}"
    if parsed.query:
        full_url += f"?{parsed.query}"
    
    # Call the transport function
    status, headers, body = transport(full_url)
    
    # Check for 200 status
    if status != 200:
        raise ValueError("Non-200 status code received")
    
    # Return the body text
    return body.decode('utf-8') if isinstance(body, bytes) else body
