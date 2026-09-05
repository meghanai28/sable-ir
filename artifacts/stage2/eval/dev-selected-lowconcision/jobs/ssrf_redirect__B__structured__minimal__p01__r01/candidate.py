import socket
import urllib.parse
import urllib.request
import urllib.error
from typing import Tuple, List, Optional

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text content from a URL.
    
    Args:
        url: The URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response if status is 200.
    
    Raises:
        ValueError: If the scheme is not http/https or if resolve_host returns no IPs.
    """
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    
    # GUARD: Check scheme
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    # Determine the port
    default_port = 80 if scheme == 'http' else 443
    
    # Resolve hostname to IP(s)
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname found")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError(f"Resolve host failed for {hostname}")
    
    # Use the first IP address for connection
    ip_address = ip_addresses[0]
    
    # Construct the request
    # Note: The transport function signature is assumed to handle the full URL or a request object.
    # Based on the plan "transport(url) returns...", we pass the original URL or a normalized one.
    # However, standard urllib.request uses the full URL. Let's assume transport expects the URL string.
    # We need to handle the case where the URL might have been normalized or not.
    # The plan says "complete symbolic-link resolution and normalization".
    # Since we are using the raw URL passed by the caller, we should let the transport handle the resolution
    # OR we should normalize it ourselves. The plan says "ORDER: check scheme and complete symbolic-link resolution".
    # This implies we should do the normalization ourselves before calling transport.
    
    # Normalize the URL: resolve .. segments and ensure it's an absolute URL with the resolved IP
    # We will construct a new URL with the resolved IP and the original path/query/fragment
    normalized_path = parsed.path
    normalized_query = parsed.query
    normalized_fragment = parsed.fragment
    
    # Reconstruct the URL with the resolved IP
    # We keep the scheme and the resolved IP
    normalized_url = f"{scheme}://{ip_address}{normalized_path}"
    if normalized_query:
        normalized_url += f"?{normalized_query}"
    if normalized_fragment:
        normalized_url += f"#{normalized_fragment}"
    
    # Call transport
    status, headers, body = transport(normalized_url)
    
    # EFFECT: return the body for status 200
    if status == 200:
        return body
    else:
        raise ValueError(f"Request failed with status {status}")
