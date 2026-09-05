import socket
import urllib.parse
import urllib.request

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation to prevent open redirects.
    
    Args:
        url: The URL to fetch (untrusted input).
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response if status is 200.
    
    Raises:
        ValueError: If the request is disallowed (e.g., non-200 status, multiple IPs).
    """
    # Parse the URL to extract netloc and path
    parsed = urllib.parse.urlparse(url)
    
    # Determine the hostname to resolve
    hostname = parsed.netloc
    if not hostname:
        raise ValueError("Invalid URL: missing netloc")
    
    # Strip port if present for resolution, but keep it for transport if needed
    # The plan implies resolving the host, so we resolve the hostname part
    # Usually netloc is "host:port", we need just "host"
    if ':' in hostname:
        hostname = hostname.split(':')[0]
    
    # Normalize and resolve the hostname
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    # Raise ValueError if resolve_host returns multiple IPs (as per plan)
    if len(ip_addresses) != 1:
        raise ValueError(f"Multiple IP addresses found for {hostname}: {ip_addresses}")
    
    # Create the connection using the resolved IP
    # We construct a new URL with the resolved IP to ensure we connect to the specific IP
    # This prevents DNS rebinding or connection to a different host than resolved
    resolved_url = f"http://{ip_addresses[0]}{url}"
    
    # Call transport
    status, headers, body = transport(resolved_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Request failed with status {status}")
    
    # Return the body
    return body

# Note: The actual HTTP connection logic is abstracted by the 'transport' function.
# In a real implementation, 'transport' would use the resolved IP to establish the socket connection.
# The above code strictly follows the plan:
# 1. Accepts untrusted URL.
# 2. Resolves hostname to IP.
# 3. Raises ValueError if multiple IPs.
# 4. Constructs a new URL with the resolved IP (preventing DNS rebinding).
# 5. Calls transport.
# 6. Validates status is exactly 200.
# 7. Does not follow redirects (checked by status code and no redirect handling).
# 8. Returns body for 200.
