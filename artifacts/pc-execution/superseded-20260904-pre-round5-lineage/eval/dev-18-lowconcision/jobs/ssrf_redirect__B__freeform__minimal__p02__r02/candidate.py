import socket
import urllib.parse
from typing import Tuple, Optional

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL following HTTP/HTTPS redirects.
    
    Args:
        url: The initial URL (absolute or relative).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status code 200.
    
    Raises:
        ValueError: If the request is disallowed, status is not 200, or validation fails.
    """
    
    # Parse the initial URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Validate scheme and port
    valid_schemes = ['http', 'https']
    if parsed_url.scheme not in valid_schemes:
        raise ValueError(f"Invalid scheme: {parsed_url.scheme}")
    
    # Determine default port
    default_port = {
        'http': 80,
        'https': 443
    }.get(parsed_url.scheme)
    
    current_scheme = parsed_url.scheme
    current_port = parsed_url.port or default_port
    current_host = parsed_url.hostname
    
    # Initial DNS resolution check
    if not current_host:
        raise ValueError("Invalid hostname in URL")
    
    try:
        ips = resolve_host(current_host)
    except Exception:
        raise ValueError(f"DNS resolution failed for {current_host}")
    
    if not ips:
        raise ValueError(f"No IP addresses found for {current_host}")
    
    # Validate public address (basic check: must be IPv4 or IPv6, not localhost/loopback)
    valid_ip = False
    for ip in ips:
        if ip.startswith(('127.', '::1')):
            continue
        # Basic check: must contain at least one digit (simple heuristic for non-local IPs)
        if any(c.isdigit() for c in ip) or ':' in ip:
            valid_ip = True
            break
    
    if not valid_ip:
        raise ValueError(f"Invalid or private IP found for {current_host}")
    
    hop_count = 0
    max_hops = 5
    
    while True:
        # Prepare the URL for transport
        # If it's a relative URL, we need to resolve it against the current base
        if not parsed_url.scheme:
            # It's a relative URL, resolve against current URL
            # Note: urllib.parse.urljoin handles this, but we need to ensure the base is absolute
            # We construct a full URL from the current state
            full_base = f"{current_scheme}://{current_host}:{current_port}"
            # If there's a path, use it, otherwise use /
            base_path = parsed_url.path if parsed_url.path else "/"
            if not parsed_url.query:
                parsed_url = urllib.parse.urljoin(full_base, parsed_url.path)
            else:
                parsed_url = urllib.parse.urljoin(full_base, f"{parsed_url.path}?{parsed_url.query}")
        else:
            # Already absolute, just ensure we have a scheme
            pass
        
        # Get the full URL string
        full_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port or default_port}{parsed_url.path}"
        
        # Call transport
        status, headers, body = transport(full_url)
        
        # Check status code
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Parse Location header if present
        location_header = headers.get('Location')
        
        if location_header:
            # Increment hop count
            hop_count += 1
            if hop_count > max_hops:
                raise ValueError(f"Too many redirects (max {max_hops})")
            
            # Parse the Location header
            loc_parsed = urllib.parse.urlparse(location_header)
            
            # Check scheme consistency
            if loc_parsed.scheme != current_scheme:
                raise ValueError(f"Location has different scheme: {loc_parsed.scheme}")
            
            # Check port consistency
            loc_port = loc_parsed.port or default_port
            if loc_port != current_port:
                raise ValueError(f"Location has different port: {loc_port}")
            
            # Resolve the new hostname
            new_host = loc_parsed.hostname
            if not new_host:
                raise ValueError(f"Invalid hostname in Location header: {location_header}")
            
            try:
                new_ips = resolve_host(new_host)
            except Exception:
                raise ValueError(f"DNS resolution failed for {new_host}")
            
            if not new_ips:
                raise ValueError(f"No IP addresses found for {new_host}")
            
            # Validate public address for new host
            new_ip_valid = False
            for ip in new_ips:
                if ip.startswith(('127.', '::1')):
                    continue
                if any(c.isdigit() for c in ip) or ':' in ip:
                    new_ip_valid = True
                    break
            
            if not new_ip_valid:
                raise ValueError(f"Invalid or private IP found for {new_host}")
            
            # Update current URL state
            current_scheme = loc_parsed.scheme
            current_host = new_host
            current_port = loc_port
            parsed_url = loc_parsed
        else:
            break
    
    return body
