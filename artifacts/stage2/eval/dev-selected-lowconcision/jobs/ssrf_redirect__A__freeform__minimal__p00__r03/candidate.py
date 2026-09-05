import socket
import urllib.parse
from typing import Tuple, List

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL with strict validation and no redirects.
    
    Args:
        url: The URL to fetch (untrusted input).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response as a string if status is 200.
    
    Raises:
        ValueError: If the request is disallowed, multiple IPs are found, or status is not 200.
    """
    # Parse the URL to extract the scheme and netloc
    parsed = urllib.parse.urlparse(url)
    
    # Determine the scheme (default to HTTP if not specified, though typically we check for HTTPS)
    # The prompt says "Accept HTTP or HTTPS on its default port".
    # We need to ensure we are dealing with HTTP/HTTPS.
    scheme = parsed.scheme.lower()
    
    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError(f"Only HTTP and HTTPS schemes are allowed. Got: {scheme}")
    
    # Extract the hostname (netloc)
    netloc = parsed.netloc
    
    # Handle port in netloc
    if ':' in netloc:
        hostname, port = netloc.rsplit(':', 1)
    else:
        hostname = netloc
        port = None
    
    # Determine the port based on scheme if not provided
    if port is None:
        if scheme == 'http':
            port = 80
        elif scheme == 'https':
            port = 443
    
    # Resolve the hostname
    try:
        ips = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname: {e}")
    
    # Check for multiple IPs (security constraint: "raise ValueError if resolve_host returns multiple IPs")
    if len(ips) > 1:
        raise ValueError(f"Multiple IP addresses found for {hostname}: {ips}")
    
    # Use the single resolved IP
    resolved_ip = ips[0]
    
    # Construct the URL for the transport function
    # We must use the resolved IP to prevent DNS rebinding issues
    # We keep the original path, query, and fragment
    path = parsed.path
    query = parsed.query
    fragment = parsed.fragment
    
    if path:
        if query:
            url_for_transport = f"http://{resolved_ip}{path}?{query}"
        else:
            url_for_transport = f"http://{resolved_ip}{path}"
    elif query:
        url_for_transport = f"http://{resolved_ip}?{query}"
    else:
        url_for_transport = f"http://{resolved_ip}"
    
    # Call the transport function
    status, headers, body = transport(url_for_transport)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Request failed with status code: {status}")
    
    # Return the body
    return body
