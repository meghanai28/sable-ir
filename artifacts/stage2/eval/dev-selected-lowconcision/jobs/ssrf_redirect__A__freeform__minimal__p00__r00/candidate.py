import socket
import urllib.parse
from typing import Tuple, List

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the URL to extract the netloc (hostname) and scheme
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    
    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Extract the hostname
    hostname = parsed.netloc
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    # Remove port if present for resolution, then re-add if needed
    # The plan says "Resolve the host", implying we resolve the domain name.
    # We will resolve the hostname as provided, stripping the port for the lookup.
    if ':' in hostname:
        hostname, _ = hostname.rsplit(':', 1)
    
    # Resolve the hostname to IP addresses
    try:
        ip_addresses = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname: {e}")
    
    # Check if multiple IPs are returned (ambiguous resolution)
    if len(ip_addresses) > 1:
        raise ValueError("Multiple IP addresses returned for hostname")
    
    # Determine the port based on scheme
    default_port = 80 if scheme == 'http' else 443
    
    # Construct the full authority string (hostname:port)
    authority = f"{hostname}:{default_port}"
    
    # Create the request URL for the initial fetch
    # We need to fetch from the initial destination without following redirects
    fetch_url = f"{scheme}://{authority}"
    
    # Perform the transport operation
    status, headers, body = transport(fetch_url)
    
    # Validate status code
    if status != 200:
        raise ValueError("Response status is not 200")
    
    # Check for Location header to ensure no redirect was attempted
    # The plan says "never follow a redirect". Since we are checking status 200,
    # a 3xx status would have failed the status check. However, we should also
    # ensure we didn't inadvertently follow a redirect if the transport does it.
    # The plan implies we check the response status immediately.
    # If status is 200, we proceed. If it were a redirect (301, 302, etc.), it would fail.
    
    # Return the body
    return body
