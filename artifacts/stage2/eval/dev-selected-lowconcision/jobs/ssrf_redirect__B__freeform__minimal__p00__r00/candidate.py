import socket
import urllib.parse
from typing import Tuple, List

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the initial URL to extract scheme and host
    parsed_url = urllib.parse.urlparse(url)
    initial_scheme = parsed_url.scheme
    initial_host = parsed_url.hostname
    initial_port = parsed_url.port
    
    # Validate scheme (only HTTP/HTTPS allowed)
    if initial_scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Resolve the initial hostname
    try:
        resolved_ips = resolve_host(initial_host)
    except Exception:
        raise ValueError("DNS resolution failed for initial host")
    
    if not resolved_ips:
        raise ValueError("DNS resolution failed for initial host")
    
    current_url = url
    max_hops = 5
    
    # Follow redirects (Location header)
    while True:
        # Get response from transport
        status, headers, body = transport(current_url)
        
        # Check status code
        if status != 200:
            raise ValueError("Response status is not 200")
        
        # Check for Location header (redirect)
        location_header = headers.get('Location')
        if location_header:
            # Parse the redirect URL
            redirect_parsed = urllib.parse.urlparse(location_header)
            
            # Resolve the redirect hostname
            try:
                resolved_redirect_ips = resolve_host(redirect_parsed.hostname)
            except Exception:
                raise ValueError("DNS resolution failed for redirect host")
            
            if not resolved_redirect_ips:
                raise ValueError("DNS resolution failed for redirect host")
            
            # Validation: scheme and port must match initial destination
            if redirect_parsed.scheme != initial_scheme:
                raise ValueError("Redirect scheme does not match initial destination scheme")
            
            if initial_port is not None and redirect_parsed.port is None:
                raise ValueError("Redirect port is missing but initial destination has a port")
            if initial_port is not None and redirect_parsed.port != initial_port:
                raise ValueError("Redirect port does not match initial destination port")
            
            # Update current URL for next hop
            current_url = location_header
            max_hops -= 1
            if max_hops < 0:
                raise ValueError("Maximum redirect hops exceeded")
        else:
            break
    
    return body

def resolve_host(hostname: str) -> List[str]:
    # Placeholder for DNS resolution; in real implementation, this would query DNS
    # For this specification, we assume it returns a list of IP addresses or raises an exception
    pass
