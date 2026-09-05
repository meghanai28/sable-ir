import socket
import urllib.parse
from typing import Tuple, Optional

def _validate_location(current_url: str, location: str) -> str:
    """
    Resolve the Location header against the current URL and validate it.
    Raises ValueError if scheme, port, or DNS validation fails.
    """
    current_parsed = urllib.parse.urlparse(current_url)
    location_parsed = urllib.parse.urlparse(location)
    
    # Check scheme
    if location_parsed.scheme not in ('http', 'https'):
        raise ValueError("Location must be HTTP or HTTPS")
    
    # Check port
    if current_parsed.port != location_parsed.port:
        raise ValueError("Location port must match current URL port")
    
    # Resolve hostname
    try:
        ip_addresses = resolve_host(location_parsed.netloc)
    except ValueError:
        raise
    
    if not ip_addresses:
        raise ValueError("Failed to resolve Location hostname")
    
    # DNS validation (basic check that IP is valid)
    for ip in ip_addresses:
        try:
            socket.inet_aton(ip)
            break
        except socket.error:
            raise ValueError("Invalid IP address in Location")
    else:
        raise ValueError("DNS validation failed for Location")
    
    return location_parsed.netloc

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL following HTTP redirects.
    
    Args:
        url: The initial URL to fetch from.
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of IP addresses.
    
    Returns:
        The body of the final response for status 200.
    
    Raises:
        ValueError: If scheme is not http/https, resolve_host fails, or redirect validation fails.
    """
    current_url = url
    max_redirects = 5
    redirect_count = 0
    
    # Initial validation
    try:
        parsed = urllib.parse.urlparse(current_url)
    except Exception:
        raise ValueError("Invalid initial URL")
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Scheme must be http or https")
    
    try:
        ip_addresses = resolve_host(parsed.netloc)
    except ValueError:
        raise
    
    if not ip_addresses:
        raise ValueError("resolve_host returned no IP addresses")
    
    # DNS validation for initial URL
    for ip in ip_addresses:
        try:
            socket.inet_aton(ip)
            break
        except socket.error:
            raise ValueError("Invalid IP address for initial URL")
    else:
        raise ValueError("DNS validation failed for initial URL")
    
    while True:
        # Make the request
        status, headers, body = transport(current_url)
        
        # Check status code
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        return body.decode('utf-8') if isinstance(body, bytes) else body
    
    # Handle redirects
    if 'location' in headers:
        redirect_count += 1
        if redirect_count > max_redirects:
            raise ValueError("Too many redirects")
        
        location = headers['location']
        
        # Resolve the new URL
        new_url = urllib.parse.urljoin(current_url, location)
        parsed_new = urllib.parse.urlparse(new_url)
        
        # Validate the new URL
        if parsed_new.scheme not in ('http', 'https'):
            raise ValueError("Redirect location scheme must be http or https")
        
        if parsed_new.port != parsed.port:
            raise ValueError("Redirect location port must match current URL port")
        
        # Resolve hostname for new URL
        try:
            ip_addresses_new = resolve_host(parsed_new.netloc)
        except ValueError:
            raise
        
        if not ip_addresses_new:
            raise ValueError("Failed to resolve redirect hostname")
        
        # DNS validation for new URL
        for ip in ip_addresses_new:
            try:
                socket.inet_aton(ip)
                break
            except socket.error:
                raise ValueError("Invalid IP address in redirect")
        else:
            raise ValueError("DNS validation failed for redirect")
        
        current_url = new_url
    
    raise ValueError("Redirect loop detected")
