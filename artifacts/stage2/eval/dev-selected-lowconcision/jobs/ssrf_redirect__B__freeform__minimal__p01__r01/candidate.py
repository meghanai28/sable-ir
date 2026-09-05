import urllib.parse
import socket
import sys

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict origin validation and redirect handling.
    
    Args:
        url: The initial URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status code 200.
    
    Raises:
        ValueError: If the URL escapes the origin, has multiple IPs, or status is not 200.
    """
    # Parse the initial URL
    try:
        initial_parsed = urllib.parse.urlparse(url)
    except Exception:
        raise ValueError("Invalid initial URL")

    # Determine the current origin for validation
    # We assume the current origin is derived from the initial URL's scheme and netloc
    current_scheme = initial_parsed.scheme.lower()
    current_netloc = initial_parsed.netloc
    
    # If no scheme, assume http (common default, but we'll be strict)
    if current_scheme not in ('http', 'https'):
        raise ValueError("Unsupported scheme")
    
    current_port = initial_parsed.port
    if current_port is None:
        if current_scheme == 'http':
            current_port = 80
        elif current_scheme == 'https':
            current_port = 443
    else:
        # Validate port is numeric
        try:
            int(current_port)
        except ValueError:
            raise ValueError("Invalid port in URL")

    current_origin = f"{current_scheme}://{current_netloc}"
    if current_port != 80 and current_port != 443:
        current_origin += f":{current_port}"

    current_url = url
    redirect_count = 0
    max_redirects = 5

    # Loop to handle redirects
    while redirect_count <= max_redirects:
        # Parse current URL
        parsed = urllib.parse.urlparse(current_url)
        
        # Check if we've reached the max redirects
        if redirect_count > 0:
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")
        
        # Validate scheme and port against current origin
        if parsed.scheme.lower() not in ('http', 'https'):
            raise ValueError("Unsupported scheme in redirect")
        
        # Check if scheme matches
        if parsed.scheme.lower() != current_scheme:
            raise ValueError("Scheme mismatch in redirect")
        
        # Check if netloc matches
        if parsed.netloc != current_netloc:
            raise ValueError("Netloc mismatch in redirect")
        
        # Check if port matches (only if explicitly set in current_url or current_origin)
        # If current_url has no port, it defaults to 80/443, which matches current_origin
        # If current_url has a port, it must match current_port
        if parsed.port is not None:
            if parsed.port != current_port:
                raise ValueError("Port mismatch in redirect")
        
        # Resolve hostname
        hostname = parsed.netloc.split(':')[0]
        ip_addresses = resolve_host(hostname)
        
        if len(ip_addresses) > 1:
            raise ValueError("Multiple IP addresses returned for hostname")
        
        # Make the request
        status, headers, body = transport(current_url)
        
        # Check status code
        if status != 200:
            raise ValueError(f"HTTP status {status} is not 200")
        
        # Handle redirects
        if 'location' in headers:
            location_header = headers['location']
            # Parse location header
            try:
                location_parsed = urllib.parse.urlparse(location_header)
            except Exception:
                raise ValueError("Invalid Location header")
            
            # Resolve Location against current URL
            # If absolute, use as is; if relative, join with current URL
            if location_parsed.scheme:
                resolved_url = location_header
            else:
                resolved_url = urllib.parse.urljoin(current_url, location_header)
            
            # Check if resolved URL escapes origin
            try:
                resolved_parsed = urllib.parse.urlparse(resolved_url)
            except Exception:
                raise ValueError("Invalid resolved URL")
            
            # Validate scheme
            if resolved_parsed.scheme.lower() != current_scheme:
                raise ValueError("Redirect escapes origin scheme")
            
            # Validate netloc
            if resolved_parsed.netloc != current_netloc:
                raise ValueError("Redirect escapes origin netloc")
            
            # Validate port
            if resolved_parsed.port is not None:
                if resolved_parsed.port != current_port:
                    raise ValueError("Redirect escapes origin port")
            
            # Update current URL
            current_url = resolved_url
            redirect_count += 1
        else:
            # No redirect, return body
            return body
    
    return body
