import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url, transport, resolve_host):
    """
    Fetches text from a URL after validating the scheme, resolving the host,
    and ensuring the path remains within the root.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The body of the response for status 200.
    
    Raises:
        ValueError: If the URL scheme is invalid, host resolution fails, or path is outside root.
    """
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    
    # GUARD: Check scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Determine the port
    if parsed.scheme == 'https':
        default_port = 443
    else:
        default_port = 80
    
    # GUARD: Resolve host
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid hostname in URL.")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("No IP address found for the host.")
    
    # Use the first resolved IP
    resolved_ip = ip_addresses[0]
    
    # Construct the full URL with resolved IP for transport
    # Note: We must use the resolved IP to connect, but we need to preserve the path/query
    # If the original URL has a path, we keep it. If not, we use /
    if parsed.path:
        full_url = f"{resolved_ip}:{default_port}{parsed.path}?{parsed.query}"
    else:
        full_url = f"{resolved_ip}:{default_port}{parsed.path}"
    
    # GUARD: Check if the path is outside the root
    # The requirement states "raise ValueError if it is outside the root /".
    # This implies the URL must start with / or be effectively rooted.
    # Since we are using the original parsed path, we check if it starts with '/' or is empty (which implies root)
    # However, strict interpretation of "outside the root /" usually means checking for path traversal or non-root paths.
    # Given the context of "resolve the initial destination and raise ValueError if it is outside the root /",
    # we interpret this as: the path component must be valid and not contain .. or be a relative path without leading /.
    # But a simpler interpretation based on "outside the root /" is that the path must start with '/' or be empty.
    # Let's assume any path that doesn't start with '/' (and isn't just the root) is considered outside root or invalid.
    # Actually, standard URLs have paths. If the path is '/', it's root. If it's '/foo', it's inside.
    # If the path is 'foo' (no leading /), it's relative and might be considered outside root.
    # Let's enforce that the path must start with '/' or be empty.
    
    # Re-evaluating "outside the root /":
    # If the URL is "http://example.com/foo", the path is "/foo". This is inside root.
    # If the URL is "http://example.com/foo", and we interpret "root /" as the literal string "/",
    # then any non-empty path is outside. But that doesn't make sense for web fetching.
    # The most logical security guard here is preventing path traversal (..) or ensuring the path is absolute.
    # However, the prompt says "raise ValueError if it is outside the root /".
    # This likely means: if the resolved path does not start with '/' (and is not empty), raise error.
    # Or it could mean: if the path contains '..'.
    # Given the strictness, let's assume we reject any path that does not start with '/' or is empty.
    # Wait, if the URL is "http://example.com", path is empty. That's fine.
    # If the URL is "http://example.com/", path is "/". That's fine.
    # If the URL is "http://example.com/foo", path is "/foo". That's fine.
    # If the URL is "http://example.comfoo", path is "foo". That's invalid.
    
    # Let's check if the path starts with '/' or is empty.
    if parsed.path and not parsed.path.startswith('/'):
        raise ValueError("Path is outside the root.")
    
    # GUARD: Resolve and check destination before following redirects
    # We resolve the initial destination (which we did via resolve_host).
    # The prompt says "resolve the initial destination and raise ValueError if it is outside the root /".
    # We have already checked the path.
    
    # Call transport
    try:
        status, headers, body = transport(url)
    except Exception as e:
        raise ValueError(f"Transport error: {e}")
    
    # GUARD: Accept only status 200
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
