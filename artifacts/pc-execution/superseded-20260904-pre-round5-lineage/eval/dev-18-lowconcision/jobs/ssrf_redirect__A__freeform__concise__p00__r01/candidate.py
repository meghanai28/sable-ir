import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the URL to extract scheme, netloc, and path
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme: only http and https are allowed
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    # Resolve the host to get IP addresses
    hostname = parsed.netloc
    if not hostname:
        hostname = 'localhost'
    
    ip_addresses = resolve_host(hostname)
    
    # Select the default port based on scheme
    default_port = 80 if scheme == 'http' else 443
    
    # Construct the full URL with the resolved host and default port for transport
    # We use the parsed components but ensure the host part is the resolved IP
    # Note: The transport function is expected to handle the full URL or we construct one.
    # Based on the spec "transport(url) returns...", we pass the constructed URL.
    # However, to be safe with the host resolution, we might need to pass a URL that uses the resolved host.
    # Since we can't change the hostname in the URL string directly without affecting the path,
    # we construct a new URL with the resolved IP.
    
    # Check if the hostname is an IP address to avoid unnecessary resolution or re-lookup
    # But the spec says "resolve the host and check the scheme before creating the connection"
    # So we use the resolved IP in the URL passed to transport.
    
    # If there are multiple IPs, we should probably use the first one or the one that matches.
    # For simplicity in this constrained environment, we use the first one.
    if not ip_addresses:
        raise ValueError(f"Could not resolve host: {hostname}")
    
    resolved_host = ip_addresses[0]
    
    # Reconstruct the URL with the resolved host, preserving the path and query
    # We must ensure the port is the default port (80 or 443)
    if parsed.port:
        # If a port was specified in the input, we are only allowed if it's the default port
        if parsed.port not in (80, 443):
            raise ValueError(f"Non-default port {parsed.port} not allowed on scheme {scheme}")
        # If it's the default port, we can keep it or omit it, but for consistency with default port behavior:
        # We will use the default port explicitly.
        pass
    
    # Build the new URL
    new_path = parsed.path
    new_query = parsed.query
    if new_query:
        new_path += f"?{new_query}"
    
    new_url = f"{scheme}://{resolved_host}:{default_port}{new_path}"
    
    # Call the transport function
    try:
        response = transport(new_url)
    except Exception as e:
        raise ValueError(f"Transport error: {e}")
    
    status, headers, body = response
    
    # Check status code
    if status != 200:
        raise ValueError(f"Non-200 status code: {status}")
    
    # Return the body as a string
    return body.decode('utf-8') if isinstance(body, bytes) else str(body)
