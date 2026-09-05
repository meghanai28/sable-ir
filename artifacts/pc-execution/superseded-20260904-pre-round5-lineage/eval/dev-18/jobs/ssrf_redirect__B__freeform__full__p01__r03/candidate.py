import socket
import urllib.parse
from typing import Tuple, List, Optional

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL following a safety plan for HTTP/HTTPS.
    
    Args:
        url: The URL to fetch (can be absolute or relative).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response for a 200 status code.
    
    Raises:
        ValueError: If the scheme, port, or hop count is invalid.
    """
    # Parse the initial URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Validate scheme and port
    valid_schemes = {'http', 'https'}
    if parsed_url.scheme not in valid_schemes:
        raise ValueError(f"Disallowed scheme: {parsed_url.scheme}")
    
    # Determine the default port for the scheme
    default_port = {'http': 80, 'https': 443}.get(parsed_url.scheme)
    actual_port = parsed_url.port
    if actual_port is None:
        actual_port = default_port
    
    # Resolve the initial hostname
    initial_hostname = parsed_url.hostname
    if initial_hostname is None:
        raise ValueError("Invalid URL: missing hostname")
    
    resolved_ips = resolve_host(initial_hostname)
    if not resolved_ips:
        raise ValueError(f"No IP addresses found for {initial_hostname}")
    
    # Build the current URL object for following redirects
    current_url = parsed_url
    
    # Maximum redirect hops
    max_hops = 5
    
    # Follow redirects
    while current_url.netloc != '' and current_url.netloc != parsed_url.netloc:
        # Check if we've exceeded max hops
        if current_url.scheme != parsed_url.scheme or current_url.port != actual_port:
            # This logic is slightly flawed in the loop condition, let's restructure based on the plan
            pass
            
        # Actually, we need to track the original scheme/port and check against it
        # Let's restart the loop logic clearly
        
        pass
    
    # Reset and implement the loop correctly
    current_url = parsed_url
    hops = 0
    
    while True:
        # Check if we've exceeded max hops
        if hops > max_hops:
            raise ValueError("Too many redirects")
        
        # Validate the current URL's scheme and port against the original request
        if current_url.scheme != parsed_url.scheme or current_url.port != actual_port:
            raise ValueError(f"Redirected to disallowed scheme/port: {current_url.scheme}:{current_url.port}")
        
        # Validate DNS resolution for the current URL
        current_hostname = current_url.hostname
        if current_hostname is None:
            raise ValueError(f"Invalid URL: missing hostname")
        
        resolved_ips = resolve_host(current_hostname)
        if not resolved_ips:
            raise ValueError(f"No IP addresses found for {current_hostname}")
        
        # Make the request
        status, headers, body = transport(current_url.geturl())
        
        # Check status code
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Check for Location header
        location_header = headers.get('Location')
        if location_header:
            hops += 1
            # Parse the Location header
            location_parsed = urllib.parse.urlparse(location_header)
            
            # Resolve the Location URL
            if location_parsed.scheme:
                # If scheme is present, use it
                final_url = location_parsed
            else:
                # If no scheme, resolve relative to current URL
                final_url = urllib.parse.urljoin(current_url.geturl(), location_header)
                final_url_parsed = urllib.parse.urlparse(final_url)
                
                # Ensure the resolved URL has the same scheme and port
                if final_url_parsed.scheme != current_url.scheme or final_url_parsed.port != current_url.port:
                    raise ValueError("Redirected to disallowed scheme/port")
                
                # Validate DNS resolution for the resolved URL
                final_hostname = final_url_parsed.hostname
                if final_hostname is None:
                    raise ValueError(f"Invalid URL: missing hostname")
                
                resolved_ips = resolve_host(final_hostname)
                if not resolved_ips:
                    raise ValueError(f"No IP addresses found for {final_hostname}")
                
                final_url = final_url_parsed
            
            # Update current_url
            current_url = final_url
            
            # Check for circular redirects (optional but good practice)
            # For simplicity, we just rely on hop count as per plan
            if hops > max_hops:
                raise ValueError("Too many redirects")
        else:
            break
    
    return body
