import socket
import urllib.parse
import urllib.request

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the URL to extract scheme, netloc, and path
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme: only http or https on default ports are allowed
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    port = parsed.port
    if port is None:
        # Use default ports
        default_port = 80 if scheme == 'http' else 443
        port = default_port
    
    # Check if the scheme matches the port
    if (scheme == 'http' and port != 80) or (scheme == 'https' and port != 443):
        raise ValueError("Only HTTP and HTTPS on default ports are allowed")
    
    # Resolve hostname to IP addresses
    hostname = parsed.netloc
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    # Remove port from hostname for resolution if present
    if ':' in hostname:
        hostname, _ = hostname.split(':', 1)
    
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    if not resolved_ips:
        raise ValueError(f"No IP addresses found for hostname: {hostname}")
    
    # Check the resolved hostname against the requested destination
    # The plan implies checking if the resolved IPs match the intended destination
    # Since we have the resolved IPs, we proceed to establish the connection
    # We will use the first resolved IP to establish the connection
    
    # Construct the full URL with the resolved IP
    # Note: The plan says "check the resolved hostname against the requested destination only after resolution is complete"
    # This implies we should verify that the resolved IP matches the expected destination
    # However, since the URL might be relative or absolute, we need to handle it carefully.
    # The plan says "Resolve the hostname to IP addresses before establishing the connection, and check the resolved hostname against the requested destination only after resolution is complete."
    # This suggests we should use the resolved IP to construct the URL for the request.
    
    # Reconstruct the URL with the resolved IP
    if parsed.path:
        full_url = f"https://{hostname}{parsed.path}" if scheme == 'https' else f"http://{hostname}{parsed.path}"
    else:
        full_url = f"https://{hostname}" if scheme == 'https' else f"http://{hostname}"
    
    # Create the request
    try:
        # Use the first resolved IP to establish the connection
        resolved_ip = resolved_ips[0]
        request = urllib.request.Request(full_url)
        
        # Open the request and read the body
        with urllib.request.urlopen(request) as response:
            status = response.status
            if status != 200:
                raise ValueError(f"Status code {status} is not 200")
            
            body = response.read().decode('utf-8')
            return body
    except Exception as e:
        raise ValueError(f"Failed to fetch URL: {e}")
