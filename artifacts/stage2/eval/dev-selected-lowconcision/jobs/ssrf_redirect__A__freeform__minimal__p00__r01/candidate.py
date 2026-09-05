import socket
import urllib.parse
from typing import Tuple, List

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL with strict validation to prevent open redirect vulnerabilities.
    
    Args:
        url: The target URL string (untrusted).
        transport: A callable that returns (status, headers, body) for a given URL.
        resolve_host: A callable that returns a list of textual IP addresses for a hostname.
    
    Returns:
        The response body as a string if status is 200.
    
    Raises:
        ValueError: If the request is disallowed (e.g., multiple IPs, non-200 status).
    """
    # Parse the URL to extract components
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme and port
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    port = parsed.port
    default_port = {'http': 80, 'https': 443}[scheme]
    
    # Determine the effective port
    if port is None:
        effective_port = default_port
    else:
        effective_port = port
    
    # Resolve the hostname
    hostname = parsed.netloc if parsed.netloc else parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    # Remove port from hostname for resolution if present in netloc
    if ':' in hostname:
        hostname = hostname.split(':')[0]
    
    # Resolve the host to IP addresses
    ip_addresses = resolve_host(hostname)
    
    # Check if multiple IPs are returned (ambiguous resolution)
    if len(ip_addresses) > 1:
        raise ValueError("Multiple IP addresses found for hostname")
    
    # Construct the connection URL for the transport function
    # We use the resolved hostname and the effective port
    # Note: The transport function is expected to handle the URL or we construct a specific one
    # Based on the plan "Resolve the host and check the status before opening the connection",
    # we assume the transport function takes the URL string.
    
    # Reconstruct the URL with resolved hostname to pass to transport
    # However, the plan says "Resolve the host... before creating the connection".
    # We will pass the original URL to transport but ensure the hostname part is what we resolved.
    # Actually, the safest interpretation is that we validate the destination using the resolved IP context.
    # But the transport function signature is transport(url).
    # Let's assume transport(url) will resolve or we just pass the url but we've already validated the hostname.
    # The plan says "check the initial public HTTP destination".
    # We will pass the original URL to transport, but we've already done the hostname check.
    
    # To be safe against redirect logic inside transport, we rely on the plan's instruction:
    # "check the initial public HTTP destination and raise ValueError if the response status is not exactly 200"
    # This implies we fetch, check status, and if not 200, we raise ValueError immediately without following.
    
    # Call transport
    status, headers, body = transport(url)
    
    # Validate status code
    if status != 200:
        raise ValueError(f"Request disallowed: status code {status} is not 200")
    
    # Return the body
    return body
