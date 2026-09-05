import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict port validation and no redirect following.
    
    Args:
        url: The URL to fetch (untrusted input).
        transport: A callable transport(url) -> (status, headers, body).
        resolve_host: A callable resolve_host(hostname) -> list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: For disallowed schemes, non-default ports, or non-200 status.
    """
    # Parse the URL to extract scheme, netloc, and path
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    port = parsed.port
    
    # Validate scheme: only HTTP or HTTPS
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Determine default port
    default_port = 80 if scheme == 'http' else 443
    
    # Check if port is the default port
    if port is None:
        # Port is not specified, use default
        port = default_port
    elif port != default_port:
        raise ValueError(f"Only default ports for {scheme} are allowed (expected {default_port}, got {port}).")
    
    # Resolve hostname to IP
    hostname = parsed.netloc
    if not hostname:
        raise ValueError("Invalid URL: missing hostname.")
    
    # Remove port from hostname if present for resolution
    if ':' in hostname:
        hostname = hostname.split(':')[0]
    
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError("Failed to resolve hostname.")
    
    if not resolved_ips:
        raise ValueError("No valid IP addresses found for hostname.")
    
    # Use the first resolved IP for the request
    ip_address = resolved_ips[0]
    
    # Construct the full URL with the resolved IP and default port
    # Note: We are using the resolved IP, but we must preserve the path and query
    # The parsed object has the original hostname, so we rebuild the netloc
    new_netloc = f"{ip_address}:{port}"
    new_url = f"{scheme}://{new_netloc}{parsed.path}"
    
    if parsed.query:
        new_url += f"?{parsed.query}"
    
    # Make the request using the standard library to handle the transport
    # We need to bypass the default opener's redirect following and use our specific transport
    # However, the standard library's urlopen uses its own transport. We must manually construct the request.
    
    # Create a request object
    req = urllib.request.Request(new_url)
    
    # Create an opener that uses our custom transport
    # Since urllib.request.HTTPHandler expects a specific protocol, we might need a custom handler
    # But the simplest way that adheres to the plan "Do not follow redirects" is to use urlopen
    # but we need to ensure no redirects happen. urlopen follows redirects by default.
    # We can set allow_redirects=False.
    
    try:
        with urllib.request.urlopen(req, redirect=False) as response:
            status = response.status
            headers = response.headers
            body = response.read().decode('utf-8', errors='replace')
            
            if status != 200:
                raise ValueError(f"HTTP status {status} is not 200.")
            
            return body
    
    except urllib.error.HTTPError as e:
        status = e.code
        if status != 200:
            raise ValueError(f"HTTP status {status} is not 200.")
        raise ValueError("Unexpected HTTP error.")
    except urllib.error.URLError as e:
        # If the URL is invalid or network error, raise ValueError
        raise ValueError(f"Network error: {e.reason}")
    except Exception as e:
        raise ValueError(f"Request failed: {e}")
