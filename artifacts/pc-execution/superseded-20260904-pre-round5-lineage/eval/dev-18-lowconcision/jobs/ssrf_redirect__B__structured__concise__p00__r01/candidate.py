import socket
import urllib.parse
from typing import Tuple, List

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL, handling redirects and DNS resolution.
    
    Args:
        url: The URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for a 200 status code.
    
    Raises:
        ValueError: If the URL is absolute, resolves to an invalid IP, or fails other checks.
    """
    
    # Parse the initial URL
    parsed = urllib.parse.urlparse(url)
    
    # GUARD: Reject absolute URLs (scheme must be http or https)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS URLs are allowed.")
    
    # GUARD: Resolve hostname and check for finite IP addresses
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("URL must contain a valid hostname.")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Failed to resolve hostname.")
    
    if not ip_addresses:
        raise ValueError("Hostname does not resolve to a finite IP address.")
    
    # Normalize the base URL for redirect handling
    base_scheme = parsed.scheme
    base_port = parsed.port
    if base_port is None:
        base_port = 80 if base_scheme == 'http' else 443
    
    # Track current URL state
    current_url = parsed
    current_scheme = base_scheme
    current_port = base_port
    current_host = parsed.hostname
    current_path = parsed.path
    current_query = parsed.query
    
    # Function to validate and resolve a new URL
    def validate_and_resolve_new_url(location: str) -> None:
        """
        Validate a Location header.
        - Must be relative to current URL if not absolute.
        - Must have same scheme and port as initial destination.
        - Must pass DNS resolution.
        """
        new_parsed = urllib.parse.urlparse(location)
        
        # If absolute, scheme must match
        if new_parsed.scheme:
            if new_parsed.scheme != current_scheme:
                raise ValueError("Redirect must have the same scheme as the initial destination.")
            # Port check for absolute
            if new_parsed.port is not None and new_parsed.port != current_port:
                raise ValueError("Redirect must have the same port as the initial destination.")
            # Hostname check
            if new_parsed.hostname is None:
                raise ValueError("Absolute redirect must have a hostname.")
            new_host = new_parsed.hostname
        else:
            # Relative URL
            if current_path == '/':
                new_parsed = urllib.parse.urlparse(f"{current_scheme}://{current_host}{location}")
            else:
                # Append to path
                if location.startswith('/'):
                    new_parsed = urllib.parse.urlparse(f"{current_scheme}://{current_host}{location}")
                else:
                    # Handle path segments
                    if current_path.endswith('/'):
                        new_parsed = urllib.parse.urlparse(f"{current_scheme}://{current_host}{location}")
                    else:
                        new_parsed = urllib.parse.urlparse(f"{current_scheme}://{current_host}{current_path}/{location}")
            new_scheme = current_scheme
            new_port = current_port
            new_host = current_host
        
        # Resolve hostname for the new URL
        try:
            new_ip_addresses = resolve_host(new_host)
        except Exception:
            raise ValueError("Failed to resolve hostname in redirect.")
        
        if not new_ip_addresses:
            raise ValueError("Redirect hostname does not resolve to a finite IP address.")
        
        # Update current URL state
        global current_url, current_scheme, current_port, current_host, current_path, current_query
        current_url = new_parsed
        current_scheme = new_scheme
        current_port = new_port
        current_host = new_host
        current_path = new_parsed.path
        current_query = new_parsed.query
    
    # Process redirects
    redirect_count = 0
    while True:
        # Call transport
        status, headers, body = transport(current_url)
        
        # GUARD: Check status code
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # GUARD: Return body for 200
        return body.decode('utf-8') if isinstance(body, bytes) else str(body)
        
        # Check for redirect
        location = headers.get('Location')
        if location:
            redirect_count += 1
            if redirect_count > 5:
                raise ValueError("Too many redirects (max 5).")
            
            # Validate and resolve the new URL
            validate_and_resolve_new_url(location)
        else:
            break
    
    raise ValueError("No body received or unexpected flow.")
