import socket
from urllib.parse import urlparse

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the URL to extract scheme, netloc, and path
    parsed = urlparse(url)
    
    # Validate scheme: must be http or https
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Extract the hostname from the netloc
    hostname = parsed.netloc
    
    # Resolve the hostname to IP address(es)
    # The plan says "resolve the hostname to its IP address(es)", we take the first valid one
    try:
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError("Failed to resolve hostname")
        # Use the first IP address for the connection
        target_ip = ip_addresses[0]
    except Exception:
        raise ValueError("Failed to resolve hostname")
    
    # Determine the port based on scheme
    default_port = 80 if scheme == 'http' else 443
    
    # Construct the full request URL for the transport function
    # We use the resolved IP and default port to ensure we connect to the public HTTP destination
    full_url = f"{scheme}://{target_ip}:{default_port}{parsed.path}"
    
    # Call the transport function
    status, headers, body = transport(full_url)
    
    # Validate status code: must be exactly 200
    if status != 200:
        raise ValueError("Request did not return status 200")
    
    # Return the response body
    return body
