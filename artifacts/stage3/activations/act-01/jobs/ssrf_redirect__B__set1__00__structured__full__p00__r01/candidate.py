import socket
import urllib.parse
import urllib.request
import urllib.error
from typing import Tuple, Any

def fetch_text(url: str, transport: Any, resolve_host: Any) -> str:
    """
    Fetch text from a URL with security validations.
    
    Args:
        url: The URL to fetch from.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response for status 200.
    
    Raises:
        ValueError: If the scheme is not http/https, DNS resolution fails,
                    or Location header validation fails.
    """
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    
    # GUARD: Check scheme
    if scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    # GUARD: Resolve host
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid URL: no hostname")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError(f"DNS resolution failed for {hostname}")
    
    if not ip_addresses:
        raise ValueError(f"No IP addresses found for {hostname}")
    
    current_url = url
    max_hops = 5
    
    # Process Location headers
    while True:
        # Make the request
        status, headers, body = transport(current_url)
        
        # Check status
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Return body if no Location header
        location_header = headers.get('Location')
        if not location_header:
            return body
        
        # Parse Location header
        try:
            location_parsed = urllib.parse.urlparse(location_header)
        except Exception:
            raise ValueError(f"Invalid Location header format: {location_header}")
        
        # GUARD: Validate Location
        # Must have same scheme and port as initial destination
        if location_parsed.scheme.lower() != scheme:
            raise ValueError(f"Location scheme mismatch: {location_parsed.scheme} vs {scheme}")
        
        # Check port
        initial_port = parsed.port
        location_port = location_parsed.port
        
        # If initial port was not specified, use 80 for http, 443 for https
        if initial_port is None:
            if scheme == 'http':
                initial_port = 80
            else:
                initial_port = 443
        
        if location_port is None:
            location_port = initial_port
        
        if location_port != initial_port:
            raise ValueError(f"Location port mismatch: {location_port} vs {initial_port}")
        
        # Check hop limit
        if max_hops <= 0:
            raise ValueError("Maximum hops exceeded")
        
        # Resolve new hostname
        new_hostname = location_parsed.hostname
        if new_hostname is None:
            raise ValueError(f"Invalid Location hostname: {location_parsed.netloc}")
        
        try:
            new_ip_addresses = resolve_host(new_hostname)
        except Exception:
            raise ValueError(f"DNS resolution failed for {new_hostname}")
        
        if not new_ip_addresses:
            raise ValueError(f"No IP addresses found for {new_hostname}")
        
        # Check if the resolved IP is valid (basic check for loop prevention)
        # We check if the IP is in the initial IP list to prevent simple loop attacks
        initial_ips_set = set(ip_addresses)
        if not new_ip_addresses:
            raise ValueError(f"No IP addresses found for {new_hostname}")
        
        # Simple loop prevention: if the new IP is the same as an initial IP, stop
        # This is a basic check; a full public-address validation would be more complex
        if new_ip_addresses and any(ip in initial_ips_set for ip in new_ip_addresses):
            raise ValueError("Potential loop detected in DNS resolution")
        
        # Update current URL
        current_url = f"{location_parsed.scheme}://{location_parsed.netloc}{location_parsed.path}{location_parsed.query}"
        max_hops -= 1
    
    return body
