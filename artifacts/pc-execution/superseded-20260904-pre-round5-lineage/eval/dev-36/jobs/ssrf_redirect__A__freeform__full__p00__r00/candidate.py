import socket
import urllib.parse
from typing import Tuple, List

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict host validation.
    
    Args:
        url: The URL to fetch (untrusted input).
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the request is disallowed (wrong protocol, non-default port, 
                   invalid status code, or host not beneath root).
    """
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    
    # Validate protocol and port
    scheme = parsed.scheme.lower()
    port = parsed.port
    
    # Accept only HTTP and HTTPS on default ports
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS protocols are allowed.")
    
    if scheme == 'http':
        expected_port = 80
    else:
        expected_port = 443
    
    if port is None:
        port = expected_port
    
    if port != expected_port:
        raise ValueError("Only default ports are allowed.")
    
    # Extract hostname
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid URL: missing hostname.")
    
    # Resolve hostname to IP addresses
    try:
        ip_addresses = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname: {e}")
    
    if not ip_addresses:
        raise ValueError("No IP addresses resolved for the hostname.")
    
    # Determine the root domain for validation
    # The root is derived from the scheme and hostname (e.g., http://example.com -> example.com)
    root_domain = f"{scheme}://{hostname}"
    
    # Check if any resolved IP is beneath the root domain
    # This implies the hostname matches the root or is a subdomain
    if hostname != root_domain.split('://')[1]:
        raise ValueError("Resolved host must be beneath the configured root.")
    
    # Call transport to get the response
    status, headers, body = transport(url)
    
    # Validate status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}. Only 200 is allowed.")
    
    # Return the body as a string
    return body if body else ""
